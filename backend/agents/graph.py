"""Revenue recovery LangGraph topology."""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.agents.common import enum_value
from backend.agents.channel_node import select_channel
from backend.agents.diagnosis_node import agent_diagnose
from backend.agents.execution_node import execute_action, log_audit
from backend.agents.experiment_node import assign_experiment, baseline_decide_node
from backend.agents.health_node import enrich_with_health
from backend.agents.state import RecoveryState
from backend.agents.strategy_node import agent_strategize
from backend.agents.triage_node import enrich_with_ml
from backend.guardrails.hitl_gate import request_approval_node
from backend.guardrails.policy_engine import policy_check_node


def build_recovery_graph() -> CompiledStateGraph:
    graph = StateGraph(RecoveryState)
    graph.add_node("enrich_ml", enrich_with_ml)
    graph.add_node("enrich_health", enrich_with_health)
    graph.add_node("assign_experiment", assign_experiment)
    graph.add_node("baseline_decide", baseline_decide_node)
    graph.add_node("agent_diagnose", agent_diagnose)
    graph.add_node("agent_strategize", agent_strategize)
    graph.add_node("select_channel", select_channel)
    graph.add_node("policy_check", policy_check_node)
    graph.add_node("request_approval", request_approval_node)
    graph.add_node("execute_action", execute_action)
    graph.add_node("log_audit", log_audit)

    graph.add_edge(START, "enrich_ml")
    graph.add_edge("enrich_ml", "enrich_health")
    graph.add_edge("enrich_health", "assign_experiment")
    graph.add_conditional_edges(
        "assign_experiment",
        _route_experiment,
        {"control": "baseline_decide", "treatment": "agent_diagnose"},
    )
    graph.add_edge("baseline_decide", "policy_check")
    graph.add_edge("agent_diagnose", "agent_strategize")
    graph.add_edge("agent_strategize", "select_channel")
    graph.add_edge("select_channel", "policy_check")
    graph.add_conditional_edges(
        "policy_check",
        _route_policy,
        {"approval": "request_approval", "stop": "log_audit", "execute": "execute_action"},
    )
    graph.add_edge("request_approval", "log_audit")
    graph.add_edge("execute_action", "log_audit")
    graph.add_edge("log_audit", END)
    return graph.compile()


def _route_experiment(state: RecoveryState) -> str:
    return "control" if enum_value(state.get("experiment_arm")) == "control" else "treatment"


def _route_policy(state: RecoveryState) -> str:
    if state.get("needs_approval", False):
        return "approval"
    action = enum_value((state.get("strategy") or {}).get("action_type", "stop"))
    return "stop" if action == "stop" else "execute"
