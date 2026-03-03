"""LangGraph workflow for audio layering pipeline"""
from langgraph.graph import StateGraph, END

from agents.analyzer import analyzer_node
from agents.vibe_director import vibe_director_node
from agents.music_supervisor import music_supervisor_node
from agents.sfx_designer import sfx_designer_node
from agents.mixing_engineer import mixing_engineer_node
from agents.renderer import renderer_node
from agents.explainer import explainer_node


def build_workflow():
    """Build and compile the audio layering workflow graph"""
    
    # Create graph with dict state
    graph = StateGraph(dict)
    
    # Add nodes
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("vibe_director", vibe_director_node)
    graph.add_node("music_supervisor", music_supervisor_node)
    graph.add_node("sfx_designer", sfx_designer_node)
    graph.add_node("mixing_engineer", mixing_engineer_node)
    graph.add_node("renderer", renderer_node)
    graph.add_node("explainer", explainer_node)
    
    # Define edges (sequential pipeline)
    graph.set_entry_point("analyzer")
    graph.add_edge("analyzer", "vibe_director")
    graph.add_edge("vibe_director", "music_supervisor")
    graph.add_edge("music_supervisor", "sfx_designer")
    graph.add_edge("sfx_designer", "mixing_engineer")
    graph.add_edge("mixing_engineer", "renderer")
    graph.add_edge("renderer", "explainer")
    graph.add_edge("explainer", END)
    
    # Compile and return
    return graph.compile()
