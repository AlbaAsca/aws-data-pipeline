"""Diagrama de arquitectura con iconos oficiales de AWS -> docs/img/architecture.png

Requiere Graphviz (`dot`) en el PATH y `pip install diagrams`.
"""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.integration import Eventbridge
from diagrams.aws.management import Cloudwatch
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
CLUSTER = {"bgcolor": "#F3F6FC", "fontcolor": "#232F3E", "pencolor": "#8C9BB5", "fontsize": "14", "style": "rounded", "labelloc": "b"}


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

    with Cluster("AWS · Terraform (tflocal ⇄ terraform)", graph_attr=CLUSTER):
        cron = Eventbridge("EventBridge\ncron 06:00 UTC")
        ingest = Lambda("Lambda ingest\nPython + duckdb")
        role = IAMRole("IAM: solo\nPutObject raw/")
        logs = Cloudwatch("CloudWatch Logs\n14 días")
        lake = S3("S3 data lake\nraw/weather/dt=…/\n*.parquet")

    with Cluster("Transformación y consumo", graph_attr=CLUSTER):
        dbt = Dbt("dbt + DuckDB\n3 modelos · 16 tests")
        wh = SQL("warehouse.duckdb")
        panel = Users("Panel Streamlit")

    with Cluster("Automatización", graph_attr=CLUSTER):
        tf = Terraform("Terraform")
        ci = GithubActions("GitHub Actions\nLocalStack e2e")

    cron >> edge("1 vez al día") >> ingest
    api >> edge("HTTPS + reintentos", "#D6246E") >> ingest
    ingest >> edge("Parquet zstd") >> lake
    ingest - Edge(style="dashed", color="#9467FD") - role
    ingest - Edge(style="dashed", color="#9467FD") - logs
    lake >> edge("read_parquet('s3://…')", "#E07B00") >> dbt >> edge() >> wh >> edge() >> panel
    tf >> Edge(style="dotted", color="#2E8B57", label="despliega", fontcolor="#1F2A44") >> cron
    ci >> Edge(style="dotted", color="#2E8B57", label="prueba", fontcolor="#1F2A44") >> tf
