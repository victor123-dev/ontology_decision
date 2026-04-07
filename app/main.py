from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.api import data_source, business_model, business_model_link, data_sensing, drive_logic, agent, test_data, drive_log, test_execution, nl_rule_interface, document_import, drive_visualization, ontology_view, action
from app.config import settings
from app.middleware_config.middleware import RequestLoggingMiddleware
from app.utils.logger import get_logger
from app.engines.data_sensing_engine import data_sensing_engine
from app.engines.drive_engine import drive_engine
from app.engines.task_manager import task_manager
from app.utils.background_task_processor import background_task_processor

logger = get_logger(__name__)

# 注册事件回调
def event_callback(event):
    drive_engine.handle_event(event)

data_sensing_engine.register_event_callback(event_callback)

# 定义应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    logger.info("启动所有引擎...")
    data_sensing_engine.start()
    drive_engine.start()
    task_manager.start()
    background_task_processor.start()
    
    yield
    
    # 关闭时
    logger.info("停止所有引擎...")
    background_task_processor.stop()
    task_manager.stop()
    drive_engine.stop()
    data_sensing_engine.stop()

app = FastAPI(
    title="Data Driven Project",
    description="数据驱动项目系统",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加请求日志记录中间件
app.add_middleware(RequestLoggingMiddleware)

# 包含API路由
app.include_router(data_source.router, prefix="/api/v1", tags=["Data Source"])
app.include_router(business_model.router, prefix="/api/v1", tags=["Business Model"])
app.include_router(business_model_link.router, prefix="/api/v1", tags=["Business Model Link"])
app.include_router(data_sensing.router, prefix="/api/v1", tags=["Data Sensing"])
app.include_router(drive_logic.router, prefix="/api/v1", tags=["Drive Logic"])
app.include_router(agent.router, prefix="/api/v1", tags=["Agent"])
app.include_router(test_data.router, prefix="/api/v1", tags=["Test Data"])
app.include_router(drive_log.router, prefix="/api/v1", tags=["Drive Log"])
app.include_router(test_execution.router, prefix="/api/v1", tags=["Test Execution"])
app.include_router(document_import.router, prefix="/api/v1", tags=["Document Import"])
app.include_router(nl_rule_interface.router, prefix="/api/v1", tags=["Natural Language Rule Interface"])
app.include_router(drive_visualization.router, prefix="/api/v1", tags=["Drive Visualization"])
app.include_router(ontology_view.router, prefix="/api/v1", tags=["Ontology View"])
app.include_router(action.router, prefix="/api/v1", tags=["Action"])

# 根路径
@app.get("/")
def read_root():
    return {"message": "Welcome to Data Driven Project", "version": settings.APP_VERSION}

if __name__ == "__main__":
    logger.info("启动Data Driven Project服务")
    logger.debug(f"服务配置: DEBUG={settings.DEBUG}, PORT={settings.PORT}")
    uvicorn.run(
        "app.main:app",  # 指定应用实例路径（模块路径:实例名）
        reload=True,     # 开启热重载（开发模式专属）
        host="0.0.0.0",# 主机（默认127.0.0.1，改为0.0.0.0可局域网访问）
        port=settings.PORT        # 端口（默认8081）
    )