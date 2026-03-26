"""Agent分配器 - 处理Agent分配和任务组调度"""
import threading
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.models.drive_logic import Task, TaskInstance
from app.models.agent import Agent
from app.utils.logger import get_logger
from app.engines.agent_executor import agent_executor
from app.utils.shared_utils import get_db_session, log_event

import traceback

logger = get_logger(__name__)


class AgentAssigner:
    """Agent分配器"""
    
    def __init__(self):
        pass
    
    def group_tasks_by_group_id(self, pending_tasks):
        """按 group_id 对任务实例进行分组"""
        groups = {}
        for task_instance in pending_tasks:
            is_group_task = task_instance.result.get('is_group_task', False)
            if is_group_task:
                group_id = task_instance.result.get('group_id')
                if group_id not in groups:
                    groups[group_id] = []
                groups[group_id].append(task_instance)
            else:
                # 单个任务使用自己的ID作为组ID
                groups[f"single_{task_instance.id}"] = [task_instance]
        return groups

    def schedule_task_group(self, group_id, group_tasks, agents, db):
        """调度任务组 - 支持多Agent"""
        # 收集任务组的所有任务和能力需求
        tasks = []
        task_capability_map = {}  # 任务ID -> 能力ID列表
        
        for task_instance in group_tasks:
            task = task_instance.task
            tasks.append(task)
            task_capability_map[task.id] = [cap.id for cap in task.capabilities]
        
        # 找到能够覆盖所有任务能力需求的Agent组合
        agent_assignment = self.find_optimal_agent_assignment(
            tasks, task_capability_map, agents
        )
        
        if agent_assignment:
            # 更新所有任务实例为 assigned 状态
            first_task_instance = group_tasks[0]
            event = first_task_instance.result.get('event', {})
            trace_id = first_task_instance.result.get('trace_id')
            
            # 为每个任务实例分配对应的Agent
            task_instance_map = {ti.task.id: ti for ti in group_tasks}
            assigned_agents = []
            
            for task_id, assigned_agent in agent_assignment.items():
                task_instance = task_instance_map[task_id]
                task_instance.assigned_agent_id = assigned_agent.id
                task_instance.status = 'assigned'
                task_instance.started_at = datetime.now()
                assigned_agents.append(assigned_agent)
            
            db.commit()
            
            # 获取去重的Agent列表和ID
            unique_agents = list({agent.id: agent for agent in assigned_agents}.values())
            unique_agent_ids = [agent.id for agent in unique_agents]
            task_ids = [task.id for task in tasks]
            agent_names = [agent.name for agent in unique_agents]
            logger.info(f"任务组 (ID: {group_id}) 已分配给 Agents: {agent_names}")
            
            # 获取任务实例ID列表用于后台线程重新查询
            task_instance_ids = [ti.id for ti in group_tasks]
            
            # 在后台线程中执行整个任务组（传入多个Agent）
            execution_thread = threading.Thread(
                target=self._execute_task_group_in_background,
                args=(unique_agent_ids, task_ids, task_instance_ids, event, trace_id, group_id)
            )
            execution_thread.daemon = True
            execution_thread.start()
        else:
            logger.warning(f"没有找到支持任务组 (ID: {group_id}) 的Agent组合")

    def find_optimal_agent_assignment(self, tasks: List[Task], 
                                     task_capability_map: Dict[int, List[int]], 
                                     available_agents: List[Agent]) -> Optional[Dict[int, Agent]]:
        """
        找到最优的Agent分配方案
        
        Args:
            tasks: 任务列表
            task_capability_map: 任务ID到能力ID列表的映射
            available_agents: 可用Agent列表
            
        Returns:
            任务ID到Agent的分配映射，如果无法分配则返回None
        """
        # 构建Agent能力映射
        agent_capability_map = {}
        for agent in available_agents:
            agent_capability_map[agent.id] = set([cap.id for cap in agent.capabilities])
        
        # 尝试为每个任务分配Agent
        assignment = {}
        unassigned_tasks = []
        
        for task in tasks:
            task_id = task.id
            required_capabilities = set(task_capability_map[task_id])
            
            # 找到能够满足该任务所有能力需求的Agent
            suitable_agents = []
            for agent in available_agents:
                agent_capabilities = agent_capability_map[agent.id]
                if required_capabilities.issubset(agent_capabilities):
                    suitable_agents.append(agent)
            
            if suitable_agents:
                # 选择第一个合适的Agent（可以优化为负载均衡等策略）
                assignment[task_id] = suitable_agents[0]
            else:
                unassigned_tasks.append(task)
        
        # 如果有任务无法分配，则整个任务组无法执行
        if unassigned_tasks:
            logger.warning(f"无法为以下任务找到合适的Agent: {[t.name for t in unassigned_tasks]}")
            return None
        
        return assignment

    def _execute_task_group_in_background(self, agent_ids: List[int], task_ids: List[int], 
                                        task_instance_ids: List[int], 
                                        event: Dict[str, Any], trace_id: str, group_id: str):
        """在后台线程中执行任务组 - 支持多Agent"""
        try:
            db = get_db_session()
            try:
                # 重新查询所有需要的对象
                agents = db.query(Agent).filter(Agent.id.in_(agent_ids)).all()
                tasks = db.query(Task).filter(Task.id.in_(task_ids)).all()
                task_instances = db.query(TaskInstance).filter(TaskInstance.id.in_(task_instance_ids)).all()
                
                # 检查任务实例状态
                for task_instance in task_instances:
                    if task_instance.status != 'assigned':
                        logger.warning(f"任务组 {group_id} 状态已改变，跳过执行")
                        return
            
                # 构建任务到Agent的映射
                task_instance_map = {ti.task.id: ti for ti in task_instances}
                task_agent_map = {}
                for agent in agents:
                    # 找到分配给这个Agent的任务
                    for task_instance in task_instances:
                        if task_instance.assigned_agent_id == agent.id:
                            if agent.id not in task_agent_map:
                                task_agent_map[agent.id] = []
                            task_agent_map[agent.id].append(task_instance.task)
            
                # 准备任务组事件数据
                group_event = {
                    **event,
                    'is_group_task': True,
                    'group_id': group_id,
                    'group_size': len(tasks),
                    'group_tasks': [{'name': t.name, 'id': t.id} for t in tasks],
                    'task_instances': [{'id': ti.id, 'index': i, 'assigned_agent_id': ti.assigned_agent_id} 
                                     for i, ti in enumerate(task_instances)],
                    'agent_assignments': {str(agent.id): agent.name for agent in agents}
                }
                
                # 执行任务组（传入多个Agent）
                execution_result = agent_executor.execute_agent_task_group(
                    agents, tasks, group_event, trace_id
                )
                
                # 更新所有任务实例状态和结果
                success = execution_result.get('success', True)
                for i, task_instance in enumerate(task_instances):
                    task_instance.status = 'completed' if success else 'failed'
                    task_instance.result = {
                        **task_instance.result,
                        'execution_result': execution_result.get('results', [{}]*len(task_instances))[i] 
                                            if 'results' in execution_result 
                                            else execution_result,
                        'completed_at': datetime.now().isoformat()
                    }
                    task_instance.completed_at = datetime.now()
                
                db.commit()
                
                # 记录任务组执行日志
                log_event('info' if success else 'error','agent_task_group_execution',f"任务组 {group_id} 执行{'成功' if success else '失败'}",{'group_id': group_id,'task_names': [task.name for task in tasks],'agent_names': [agent.name for agent in agents],'success': success,'execution_result': execution_result},trace_id)
                
                if success:
                    logger.info(f"任务组 {group_id} 执行成功")
                else:
                    logger.error(f"任务组 {group_id} 执行失败")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"执行任务组失败: {str(e)}")
            logger.error(traceback.format_exc())