"""
LangGraph Workflow Definition for Audio Layering Pipeline
=========================================================

Defines the directed acyclic graph (DAG) that orchestrates the multi-agent
audio processing pipeline. Each node is an agent that transforms the shared
state and produces artifacts.

Pipeline Flow:
    analyzer → vibe_director → music_supervisor → sfx_designer 
             → mixing_engineer → renderer → explainer → END

Each agent reads from state.artifacts and writes new artifacts back.
The state dict flows through all nodes, accumulating results.
"""
from langgraph.graph import StateGraph, END

# Import all agent node functions
from agents.analyzer import analyzer_node
from agents.vibe_director import vibe_director_node
from agents.music_supervisor import music_supervisor_node
from agents.sfx_designer import sfx_designer_node
from agents.mixing_engineer import mixing_engineer_node
from agents.renderer import renderer_node
from agents.explainer import explainer_node


def build_workflow():
    """
    Build and compile the audio layering workflow graph.
    
    Returns:
        CompiledGraph: A runnable LangGraph workflow that accepts a state dict
                       and returns the final state after all agents complete.
    """
    # Create graph with dict state (flexible key-value storage)
    graph = StateGraph(dict)
    
    # Register agent nodes
    # Each node receives the full state dict and returns an updated version
    graph.add_node("analyzer", analyzer_node)           # Extract audio, detect speech
    graph.add_node("vibe_director", vibe_director_node) # Classify mood/tone
    graph.add_node("music_supervisor", music_supervisor_node)  # Select music tracks
    graph.add_node("sfx_designer", sfx_designer_node)   # Place sound effects
    graph.add_node("mixing_engineer", mixing_engineer_node)    # Configure ducking
    graph.add_node("renderer", renderer_node)           # Mix & mux final video
    graph.add_node("explainer", explainer_node)         # Generate explanation
    
    # Define sequential pipeline edges
    # (Could be made parallel or conditional in future versions)
    graph.set_entry_point("analyzer")
    graph.add_edge("analyzer", "vibe_director")
    graph.add_edge("vibe_director", "music_supervisor")
    graph.add_edge("music_supervisor", "sfx_designer")
    graph.add_edge("sfx_designer", "mixing_engineer")
    graph.add_edge("mixing_engineer", "renderer")
    graph.add_edge("renderer", "explainer")
    graph.add_edge("explainer", END)  # Terminal node
    
    # Compile into executable workflow
    return graph.compile()
