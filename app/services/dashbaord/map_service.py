from typing import Dict, List

from app.services.dashbaord.sdk_client import get_ontology_client
from app.vo.alertdashboard.map_vo import MapNodeVO, MapRouteVO


class MapService:
    """地图服务类，使用OntologyClient查询地图数据"""

    def get_all_nodes(self) -> List[MapNodeVO]:
        """获取所有地图节点"""
        client = get_ontology_client()
        nodes = client.models.SupplyChainMapNodes.find()

        return [
            MapNodeVO(
                id=node.node_id or "",
                name=node.node_name or "",
                type=node.node_type or "",
                city=node.city or "",
                lat=float(node.latitude) if node.latitude else 0.0,
                lng=float(node.longitude) if node.longitude else 0.0
            )
            for node in nodes
        ]

    def get_all_routes(self) -> List[MapRouteVO]:
        """获取所有地图路由"""
        client = get_ontology_client()
        routes = client.models.SupplyChainMapRoutes.find()

        return [
            MapRouteVO(
                from_=route.start_node or "",
                to=route.end_node or "",
                type=route.route_type or "",
                active=route.is_active if route.is_active is not None else False
            )
            for route in routes
        ]

    def get_map_data(self) -> Dict[str, List]:
        """获取完整的地图数据（节点和路由）"""
        return {
            "nodes": [node.model_dump(by_alias=True) for node in self.get_all_nodes()],
            "routes": [route.model_dump(by_alias=True) for route in self.get_all_routes()]
        }
