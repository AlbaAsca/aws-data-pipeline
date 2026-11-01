"""Diagrama de arquitectura con iconos oficiales de AWS -> docs/img/architecture.png

Requiere Graphviz (`dot`) en el PATH y `pip install diagrams`.
"""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.devtools import Codebuild
from diagrams.aws.integration import SNS, SQS, Eventbridge
from diagrams.aws.management import CloudwatchAlarm, ParameterStore
from diagrams.aws.security import IAMRole
from diagrams.aws.storage import S3
from diagrams.generic.database import SQL
from diagrams.onprem.analytics import Dbt
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.client import Users
from diagrams.onprem.iac import Terraform
from diagrams.onprem.network import Internet

OUT = Path(__file__).resolve().parents[1] / "docs" / "img" / "architecture"

GRAPH = {"bgcolor": "#FFFFFF", "pad": "0.4", "fontcolor": "#1F2A44", "fontsize": "22", "splines": "spline"}
NODE = {"fontcolor": "#1F2A44", "fontsize": "12"}
CLUSTER = {
    "bgcolor": "#F3F6FC",
    "fontcolor": "#232F3E",
    "pencolor": "#8C9BB5",
    "fontsize": "14",
    "style": "rounded",
    "labelloc": "b",
}


def edge(label: str = "", color: str = "#0B7FAB") -> Edge:
    return Edge(label=label, color=color, fontcolor="#1F2A44", fontsize="11", penwidth="2")


with Diagram(
    "aws-data-pipeline",
    filename=str(OUT),
    outformat="png",
    show=False,
    direction="LR",
    graph_attr=GRAPH,
    node_attr=NODE,
):
    api = Internet("Open-Meteo API\n(JSON horario)")

    with Cluster("Despliegue", graph_attr=CLUSTER):
        ci = GithubActions("GitHub Actions\nCI (LocalStack) · Deploy")
        oidc = IAMRole("Rol OIDC\nsin claves")
        tf = Terraform("Terraform\nestado en S3")

    with Cluster("AWS", graph_attr=CLUSTER):
        with Cluster("Ingesta", graph_attr=CLUSTER):
            cron = Eventbridge("EventBridge\n06:00 UTC")
            cities = ParameterStore("SSM\nciudades")
            ingest = Lambda("Lambda ingest\nPython + duckdb")
            lake = S3("S3 data lake\nraw/dt=…/*.parquet\nwarehouse/")

        with Cluster("Alertas", graph_attr=CLUSTER):
            dlq = SQS("DLQ")
            alarm = CloudwatchAlarm("Alarmas\nErrors · DLQ")
            sns = SNS("SNS → email")

        with Cluster("Transformación", graph_attr=CLUSTER):
            cron_dbt = Eventbridge("EventBridge\n07:00 UTC")
            build = Codebuild("CodeBuild\ndbt build")

    with Cluster("Consumo", graph_attr=CLUSTER):
        dbt = Dbt("dbt + DuckDB\n3 modelos · 16 tests")
        wh = SQL("warehouse.duckdb")
        panel = Users("Panel Streamlit")

    ci >> edge("OIDC") >> oidc >> edge() >> tf
    tf >> Edge(style="dotted", color="#2E8B57", label="despliega", fontcolor="#1F2A44") >> cron

    cron >> edge("1 vez al día") >> ingest
    cities >> edge("lista") >> ingest
    api >> edge("HTTPS + reintentos", "#D6246E") >> ingest
    ingest >> edge("Parquet zstd") >> lake
    ingest >> edge("si falla", "#D6246E") >> dlq
    ingest >> Edge(style="dashed", color="#D6246E") >> alarm
    dlq >> Edge(style="dashed", color="#D6246E") >> alarm >> edge(color="#D6246E") >> sns

    cron_dbt >> edge() >> build >> edge("read_parquet", "#E07B00") >> dbt
    lake >> Edge(style="dashed", color="#E07B00") >> build
    dbt >> edge() >> wh >> edge() >> panel
