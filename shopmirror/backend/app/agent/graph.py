"""
agent/graph.py — LangGraph state machine + AsyncPostgresSaver wiring.

Graph:
  planner → approval_gate → executor → verifier → planner (loop)
                                                 ↘ reporter (terminal)

AsyncPostgresSaver is initialised from DATABASE_URL on first use so the
graph can persist state across the approval interrupt.
"""

from __future__ import annotations

import os
import logging
from typing import Optional

from langgraph.graph import StateGraph, END

from app.agent.state import StoreOptimizationState
from app.agent.nodes import (
    planner_node,
    approval_gate_node,
    executor_node,
    verifier_node,
    reporter_node,
    route_after_planner,
    route_after_verifier,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graph definition
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    workflow = StateGraph(StoreOptimizationState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("approval_gate", approval_gate_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("reporter", reporter_node)

    workflow.set_entry_point("planner")

    # planner → approval_gate always (approval_gate is a pass-through since
    # approved_fix_ids are set in the initial state by POST /execute)
    workflow.add_edge("planner", "approval_gate")

    # approval_gate → conditional
    workflow.add_conditional_edges(
        "approval_gate",
        route_after_planner,
        {"executor": "executor", "reporter": "reporter"},
    )

    workflow.add_edge("executor", "verifier")

    workflow.add_conditional_edges(
        "verifier",
        route_after_verifier,
        {"executor": "executor", "planner": "planner"},
    )

    workflow.add_edge("reporter", END)

    return workflow


# ---------------------------------------------------------------------------
# Compiled graph with AsyncPostgresSaver
# ---------------------------------------------------------------------------

_compiled_graph = None


async def get_compiled_graph():
    """Return a compiled graph with AsyncPostgresSaver wired in.

    Initialised lazily on first call. The checkpointer uses the same
    DATABASE_URL as the main asyncpg pool.
    """
    global _compiled_graph
    if _compiled_graph is not None:
        return _compiled_graph

    database_url = os.getenv("DATABASE_URL", "")
    workflow = build_graph()

    if database_url:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            # Convert asyncpg URI to psycopg URI format if needed
            pg_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
            checkpointer = await AsyncPostgresSaver.from_conn_string(pg_url)
            await checkpointer.setup()
            _compiled_graph = workflow.compile(checkpointer=checkpointer)
            logger.info("LangGraph compiled with AsyncPostgresSaver")
        except Exception as exc:
            logger.warning(
                "AsyncPostgresSaver unavailable (%s) — compiling without checkpointer", exc
            )
            _compiled_graph = workflow.compile()
    else:
        logger.warning("DATABASE_URL not set — compiling LangGraph without checkpointer")
        _compiled_graph = workflow.compile()

    return _compiled_graph


# ---------------------------------------------------------------------------
# run_fix_agent — entry point called from POST /execute route
# ---------------------------------------------------------------------------

async def run_fix_agent(initial_state: StoreOptimizationState) -> dict:
    """Run the fix agent to completion.

    Uses thread_id = job_id so LangGraph can persist and resume per job.
    Returns the final state dict.
    """
    graph = await get_compiled_graph()
    # LangGraph counts node traversals against recursion_limit. Our fix loop
    # can legitimately exceed the small default when multiple approved fixes
    # each pass through planner -> approval_gate -> executor -> verifier.
    config = {
        "configurable": {"thread_id": initial_state["job_id"]},
        "recursion_limit": 100,
    }

    final_state: Optional[dict] = None
    async for chunk in graph.astream(initial_state, config=config):
        final_state = chunk

    return final_state or {}
