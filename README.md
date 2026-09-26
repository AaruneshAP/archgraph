# Codebase Architecture Visualizer

> 🚀 **Try it live:** [https://archgraph.vercel.app](https://archgraph.vercel.app)

> Turn any Python codebase into an interactive, high-level architectural diagram with dependency mapping, git revision diffing, and AI-powered narration.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-3B82C4?style=for-the-badge&logo=vercel)](https://archgraph.vercel.app)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![Free Tier](https://img.shields.io/badge/Cost-100%25%20Free%20Tier-success?style=for-the-badge)](#tech-stack)

---

## Live Demo

Explore public GitHub repositories directly in the browser:  
🔗 **[https://archgraph.vercel.app](https://archgraph.vercel.app)**

---

## Architectural Diagram

Here is the Codebase Architecture Visualizer analyzing its own core architecture (`self.mmd`):

```mermaid
%%{init: {'flowchart': {'defaultRenderer': 'elk', 'nodeSpacing': 30, 'rankSpacing': 40}, 'maxTextSize': 2000000}}%%
graph TD
    %% Nodes
    api_analyze["<div class='node-card' style='border-left:4px solid #E8874A;'><div class='node-type' style='color:#E8874A;'>MODULE</div><div class='node-name'>api.analyze</div><div class='node-sub' title='analyze.py'>analyze.py</div></div>"]
    api_analyze_handler["<div class='node-card' style='border-left:4px solid #8B6FD1;'><div class='node-type' style='color:#8B6FD1;'>CLASS</div><div class='node-name'>handler</div><div class='node-sub' title='extends BaseHTTPRequestHandler'>extends BaseHTTPRequestHandler</div></div>"]
    api_analyze_parse_github_url["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>parse_github_url()</div><div class='node-sub' title='analyze.py'>analyze.py</div></div>"]
    api_analyze_fetch_repo_tree["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>fetch_repo_tree()</div><div class='node-sub' title='analyze.py'>analyze.py</div></div>"]
    api_analyze_fetch_raw_file["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>fetch_raw_file()</div><div class='node-sub' title='analyze.py'>analyze.py</div></div>"]
    codebase_graph["<div class='node-card' style='border-left:4px solid #E8874A;'><div class='node-type' style='color:#E8874A;'>MODULE</div><div class='node-name'>codebase_graph</div><div class='node-sub' title='codebase_graph.py'>codebase_graph.py</div></div>"]
    codebase_graph_FileParseResult["<div class='node-card' style='border-left:4px solid #8B6FD1;'><div class='node-type' style='color:#8B6FD1;'>CLASS</div><div class='node-name'>FileParseResult</div><div class='node-sub' title='codebase_graph.py'>codebase_graph.py</div></div>"]
    codebase_graph_resolve_callee_name["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>resolve_callee_name()</div><div class='node-sub' title='codebase_graph.py'>codebase_graph.py</div></div>"]
    codebase_graph_resolve_base_name["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>resolve_base_name()</div><div class='node-sub' title='codebase_graph.py'>codebase_graph.py</div></div>"]
    codebase_graph_get_module_name_from_relpath["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>get_module_name_from_relpath()</div><div class='node-sub' title='codebase_graph.py'>codebase_graph.py</div></div>"]
    codebase_graph_get_module_name["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>get_module_name()</div><div class='node-sub' title='codebase_graph.py'>codebase_graph.py</div></div>"]
    codebase_graph_resolve_relative_import["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>resolve_relative_import()</div><div class='node-sub' title='codebase_graph.py'>codebase_graph.py</div></div>"]
    codebase_graph_parse_python_code["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>parse_python_code()</div><div class='node-sub' title='codebase_graph.py'>codebase_graph.py</div></div>"]
    codebase_graph_parse_python_file["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>parse_python_file()</div><div class='node-sub' title='codebase_graph.py'>codebase_graph.py</div></div>"]
    codebase_graph_find_all_python_files["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>find_all_python_files()</div><div class='node-sub' title='codebase_graph.py'>codebase_graph.py</div></div>"]
    codebase_graph_assemble_graph["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>assemble_graph()</div><div class='node-sub' title='codebase_graph.py'>codebase_graph.py</div></div>"]
    codebase_graph_build_graph_from_sources["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>build_graph_from_sources()</div><div class='node-sub' title='codebase_graph.py'>codebase_graph.py</div></div>"]
    codebase_graph_build_graph["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>build_graph()</div><div class='node-sub' title='codebase_graph.py'>codebase_graph.py</div></div>"]
    codebase_graph_parse_codebase_cli["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>parse_codebase_cli()</div><div class='node-sub' title='codebase_graph.py'>codebase_graph.py</div></div>"]
    dev_server["<div class='node-card' style='border-left:4px solid #E8874A;'><div class='node-type' style='color:#E8874A;'>MODULE</div><div class='node-name'>dev_server</div><div class='node-sub' title='dev_server.py'>dev_server.py</div></div>"]
    dev_server_DevServerHandler["<div class='node-card' style='border-left:4px solid #8B6FD1;'><div class='node-type' style='color:#8B6FD1;'>CLASS</div><div class='node-name'>DevServerHandler</div><div class='node-sub' title='extends AnalyzeHandler'>extends AnalyzeHandler</div></div>"]
    dev_server_run["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>run()</div><div class='node-sub' title='dev_server.py'>dev_server.py</div></div>"]
    diff_graph["<div class='node-card' style='border-left:4px solid #E8874A;'><div class='node-type' style='color:#E8874A;'>MODULE</div><div class='node-name'>diff_graph</div><div class='node-sub' title='diff_graph.py'>diff_graph.py</div></div>"]
    diff_graph_get_graph_at_revision["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>get_graph_at_revision()</div><div class='node-sub' title='diff_graph.py'>diff_graph.py</div></div>"]
    diff_graph_diff_graphs["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>diff_graphs()</div><div class='node-sub' title='diff_graph.py'>diff_graph.py</div></div>"]
    diff_graph_main["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>main()</div><div class='node-sub' title='entrypoint'>entrypoint</div></div>"]
    graph_to_mermaid["<div class='node-card' style='border-left:4px solid #E8874A;'><div class='node-type' style='color:#E8874A;'>MODULE</div><div class='node-name'>graph_to_mermaid</div><div class='node-sub' title='graph_to_mermaid.py'>graph_to_mermaid.py</div></div>"]
    graph_to_mermaid_sanitize_mermaid_id["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>sanitize_mermaid_id()</div><div class='node-sub' title='graph_to_mermaid.py'>graph_to_mermaid.py</div></div>"]
    graph_to_mermaid_make_node_card_html["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>make_node_card_html()</div><div class='node-sub' title='graph_to_mermaid.py'>graph_to_mermaid.py</div></div>"]
    graph_to_mermaid_graph_to_mermaid["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>graph_to_mermaid()</div><div class='node-sub' title='graph_to_mermaid.py'>graph_to_mermaid.py</div></div>"]
    graph_to_mermaid_count_rendered_nodes["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>count_rendered_nodes()</div><div class='node-sub' title='graph_to_mermaid.py'>graph_to_mermaid.py</div></div>"]
    graph_to_mermaid_count_rendered_edges["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>count_rendered_edges()</div><div class='node-sub' title='graph_to_mermaid.py'>graph_to_mermaid.py</div></div>"]
    graph_to_mermaid_get_collapse_info["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>get_collapse_info()</div><div class='node-sub' title='graph_to_mermaid.py'>graph_to_mermaid.py</div></div>"]
    graph_to_mermaid_generate_html_viewer["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>generate_html_viewer()</div><div class='node-sub' title='graph_to_mermaid.py'>graph_to_mermaid.py</div></div>"]
    graph_to_mermaid_render_diagram_files["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>render_diagram_files()</div><div class='node-sub' title='graph_to_mermaid.py'>graph_to_mermaid.py</div></div>"]
    graph_to_mermaid_render_diagram_cli["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>render_diagram_cli()</div><div class='node-sub' title='graph_to_mermaid.py'>graph_to_mermaid.py</div></div>"]
    narrate_diff["<div class='node-card' style='border-left:4px solid #E8874A;'><div class='node-type' style='color:#E8874A;'>MODULE</div><div class='node-name'>narrate_diff</div><div class='node-sub' title='narrate_diff.py'>narrate_diff.py</div></div>"]
    narrate_diff_format_diff_for_llm["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>format_diff_for_llm()</div><div class='node-sub' title='narrate_diff.py'>narrate_diff.py</div></div>"]
    narrate_diff_narrate_diff["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>narrate_diff()</div><div class='node-sub' title='narrate_diff.py'>narrate_diff.py</div></div>"]
    narrate_diff_narrate_architecture["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>narrate_architecture()</div><div class='node-sub' title='narrate_diff.py'>narrate_diff.py</div></div>"]
    parse_codebase["<div class='node-card' style='border-left:4px solid #E8874A;'><div class='node-type' style='color:#E8874A;'>MODULE</div><div class='node-name'>parse_codebase</div><div class='node-sub' title='parse_codebase.py'>parse_codebase.py</div></div>"]
    render_diagram["<div class='node-card' style='border-left:4px solid #E8874A;'><div class='node-type' style='color:#E8874A;'>MODULE</div><div class='node-name'>render_diagram</div><div class='node-sub' title='render_diagram.py'>render_diagram.py</div></div>"]
    sample_package_app["<div class='node-card' style='border-left:4px solid #E8874A;'><div class='node-type' style='color:#E8874A;'>MODULE</div><div class='node-name'>sample_package.app</div><div class='node-sub' title='app.py'>app.py</div></div>"]
    sample_package_app_AppService["<div class='node-card' style='border-left:4px solid #8B6FD1;'><div class='node-type' style='color:#8B6FD1;'>CLASS</div><div class='node-name'>AppService</div><div class='node-sub' title='extends BaseService'>extends BaseService</div></div>"]
    sample_package_app_main["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>main()</div><div class='node-sub' title='entrypoint'>entrypoint</div></div>"]
    sample_package_base["<div class='node-card' style='border-left:4px solid #E8874A;'><div class='node-type' style='color:#E8874A;'>MODULE</div><div class='node-name'>sample_package.base</div><div class='node-sub' title='base.py'>base.py</div></div>"]
    sample_package_base_BaseService["<div class='node-card' style='border-left:4px solid #8B6FD1;'><div class='node-type' style='color:#8B6FD1;'>CLASS</div><div class='node-name'>BaseService</div><div class='node-sub' title='base.py'>base.py</div></div>"]
    sample_package_utils["<div class='node-card' style='border-left:4px solid #E8874A;'><div class='node-type' style='color:#E8874A;'>MODULE</div><div class='node-name'>sample_package.utils</div><div class='node-sub' title='utils.py'>utils.py</div></div>"]
    sample_package_utils_format_message["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>format_message()</div><div class='node-sub' title='utils.py'>utils.py</div></div>"]
    sample_package_utils_compute_total["<div class='node-card' style='border-left:4px solid #2FA89C;'><div class='node-type' style='color:#2FA89C;'>FUNCTION</div><div class='node-name'>compute_total()</div><div class='node-sub' title='utils.py'>utils.py</div></div>"]
    test_api["<div class='node-card' style='border-left:4px solid #E8874A;'><div class='node-type' style='color:#E8874A;'>MODULE</div><div class='node-name'>test_api</div><div class='node-sub' title='test_api.py'>test_api.py</div></div>"]
    test_api_TestApiAnalyze["<div class='node-card' style='border-left:4px solid #8B6FD1;'><div class='node-type' style='color:#8B6FD1;'>CLASS</div><div class='node-name'>TestApiAnalyze</div><div class='node-sub' title='extends TestCase'>extends TestCase</div></div>"]
    test_diff["<div class='node-card' style='border-left:4px solid #E8874A;'><div class='node-type' style='color:#E8874A;'>MODULE</div><div class='node-name'>test_diff</div><div class='node-sub' title='test_diff.py'>test_diff.py</div></div>"]
    test_diff_TestDiffGraphsPure["<div class='node-card' style='border-left:4px solid #8B6FD1;'><div class='node-type' style='color:#8B6FD1;'>CLASS</div><div class='node-name'>TestDiffGraphsPure</div><div class='node-sub' title='extends TestCase'>extends TestCase</div></div>"]
    test_diff_TestGetGraphAtRevision["<div class='node-card' style='border-left:4px solid #8B6FD1;'><div class='node-type' style='color:#8B6FD1;'>CLASS</div><div class='node-name'>TestGetGraphAtRevision</div><div class='node-sub' title='extends TestCase'>extends TestCase</div></div>"]
    test_diff_TestEndToEndSamplePackageDiff["<div class='node-card' style='border-left:4px solid #8B6FD1;'><div class='node-type' style='color:#8B6FD1;'>CLASS</div><div class='node-name'>TestEndToEndSamplePackageDiff</div><div class='node-sub' title='extends TestCase'>extends TestCase</div></div>"]
    test_graph["<div class='node-card' style='border-left:4px solid #E8874A;'><div class='node-type' style='color:#E8874A;'>MODULE</div><div class='node-name'>test_graph</div><div class='node-sub' title='test_graph.py'>test_graph.py</div></div>"]
    test_graph_TestCodebaseGraph["<div class='node-card' style='border-left:4px solid #8B6FD1;'><div class='node-type' style='color:#8B6FD1;'>CLASS</div><div class='node-name'>TestCodebaseGraph</div><div class='node-sub' title='extends TestCase'>extends TestCase</div></div>"]
    test_narrate["<div class='node-card' style='border-left:4px solid #E8874A;'><div class='node-type' style='color:#E8874A;'>MODULE</div><div class='node-name'>test_narrate</div><div class='node-sub' title='test_narrate.py'>test_narrate.py</div></div>"]
    test_narrate_TestNarrateDiff["<div class='node-card' style='border-left:4px solid #8B6FD1;'><div class='node-type' style='color:#8B6FD1;'>CLASS</div><div class='node-name'>TestNarrateDiff</div><div class='node-sub' title='extends TestCase'>extends TestCase</div></div>"]
    test_render["<div class='node-card' style='border-left:4px solid #E8874A;'><div class='node-type' style='color:#E8874A;'>MODULE</div><div class='node-name'>test_render</div><div class='node-sub' title='test_render.py'>test_render.py</div></div>"]
    test_render_TestGraphToMermaid["<div class='node-card' style='border-left:4px solid #8B6FD1;'><div class='node-type' style='color:#8B6FD1;'>CLASS</div><div class='node-name'>TestGraphToMermaid</div><div class='node-sub' title='extends TestCase'>extends TestCase</div></div>"]

    %% Edges
    %% Contains Edges
    api_analyze --> api_analyze_handler
    api_analyze --> api_analyze_parse_github_url
    api_analyze --> api_analyze_fetch_repo_tree
    api_analyze --> api_analyze_fetch_raw_file
    codebase_graph --> codebase_graph_FileParseResult
    codebase_graph --> codebase_graph_resolve_callee_name
    codebase_graph --> codebase_graph_resolve_base_name
    codebase_graph --> codebase_graph_get_module_name_from_relpath
    codebase_graph --> codebase_graph_get_module_name
    codebase_graph --> codebase_graph_resolve_relative_import
    codebase_graph --> codebase_graph_parse_python_code
    codebase_graph --> codebase_graph_parse_python_file
    codebase_graph --> codebase_graph_find_all_python_files
    codebase_graph --> codebase_graph_assemble_graph
    codebase_graph --> codebase_graph_build_graph_from_sources
    codebase_graph --> codebase_graph_build_graph
    codebase_graph --> codebase_graph_parse_codebase_cli
    dev_server --> dev_server_DevServerHandler
    dev_server --> dev_server_run
    diff_graph --> diff_graph_get_graph_at_revision
    diff_graph --> diff_graph_diff_graphs
    diff_graph --> diff_graph_main
    graph_to_mermaid --> graph_to_mermaid_sanitize_mermaid_id
    graph_to_mermaid --> graph_to_mermaid_make_node_card_html
    graph_to_mermaid --> graph_to_mermaid_graph_to_mermaid
    graph_to_mermaid --> graph_to_mermaid_count_rendered_nodes
    graph_to_mermaid --> graph_to_mermaid_count_rendered_edges
    graph_to_mermaid --> graph_to_mermaid_get_collapse_info
    graph_to_mermaid --> graph_to_mermaid_generate_html_viewer
    graph_to_mermaid --> graph_to_mermaid_render_diagram_files
    graph_to_mermaid --> graph_to_mermaid_render_diagram_cli
    narrate_diff --> narrate_diff_format_diff_for_llm
    narrate_diff --> narrate_diff_narrate_diff
    narrate_diff --> narrate_diff_narrate_architecture
    sample_package_app --> sample_package_app_AppService
    sample_package_app --> sample_package_app_main
    sample_package_base --> sample_package_base_BaseService
    sample_package_utils --> sample_package_utils_format_message
    sample_package_utils --> sample_package_utils_compute_total
    test_api --> test_api_TestApiAnalyze
    test_diff --> test_diff_TestDiffGraphsPure
    test_diff --> test_diff_TestGetGraphAtRevision
    test_diff --> test_diff_TestEndToEndSamplePackageDiff
    test_graph --> test_graph_TestCodebaseGraph
    test_narrate --> test_narrate_TestNarrateDiff
    test_render --> test_render_TestGraphToMermaid
    %% Inherits Edges
    sample_package_app_AppService -.- sample_package_base_BaseService
    %% Imports Edges
    api_analyze -.- codebase_graph
    api_analyze -.- graph_to_mermaid
    api_analyze -.- narrate_diff
    dev_server -.- api_analyze
    diff_graph -.- codebase_graph
    diff_graph -.- narrate_diff
    parse_codebase -.- codebase_graph
    render_diagram -.- graph_to_mermaid
    test_api -.- api_analyze
    test_api -.- codebase_graph
    test_diff -.- diff_graph
    test_graph -.- codebase_graph
    test_narrate -.- diff_graph
    test_narrate -.- narrate_diff
    test_render -.- graph_to_mermaid
    %% Calls Edges
    api_analyze_handler --> api_analyze_parse_github_url
    api_analyze_handler --> api_analyze_fetch_repo_tree
    api_analyze_handler --> codebase_graph_build_graph_from_sources
    api_analyze_handler --> graph_to_mermaid
    api_analyze_handler --> graph_to_mermaid_count_rendered_edges
    api_analyze_handler --> graph_to_mermaid_count_rendered_nodes
    api_analyze_handler --> graph_to_mermaid_get_collapse_info
    api_analyze_handler --> narrate_diff_narrate_architecture
    codebase_graph_resolve_base_name --> codebase_graph_resolve_callee_name
    codebase_graph_get_module_name --> codebase_graph_get_module_name_from_relpath
    codebase_graph_parse_python_code --> codebase_graph_get_module_name_from_relpath
    codebase_graph_parse_python_code --> codebase_graph_FileParseResult
    codebase_graph_parse_python_code --> codebase_graph_resolve_relative_import
    codebase_graph_parse_python_code --> codebase_graph_resolve_callee_name
    codebase_graph_parse_python_code --> codebase_graph_resolve_base_name
    codebase_graph_parse_python_file --> codebase_graph_parse_python_code
    codebase_graph_build_graph_from_sources --> codebase_graph_parse_python_code
    codebase_graph_build_graph_from_sources --> codebase_graph_assemble_graph
    codebase_graph_build_graph --> codebase_graph_find_all_python_files
    codebase_graph_build_graph --> codebase_graph_parse_python_file
    codebase_graph_build_graph --> codebase_graph_assemble_graph
    codebase_graph_parse_codebase_cli --> codebase_graph_build_graph
    diff_graph_get_graph_at_revision --> codebase_graph_build_graph
    diff_graph_main --> diff_graph_get_graph_at_revision
    diff_graph_main --> diff_graph_diff_graphs
    diff_graph_main --> narrate_diff
    graph_to_mermaid --> graph_to_mermaid_sanitize_mermaid_id
    graph_to_mermaid --> graph_to_mermaid_make_node_card_html
    graph_to_mermaid_generate_html_viewer --> graph_to_mermaid_get_collapse_info
    graph_to_mermaid_generate_html_viewer --> graph_to_mermaid_count_rendered_nodes
    graph_to_mermaid_generate_html_viewer --> graph_to_mermaid_count_rendered_edges
    graph_to_mermaid_render_diagram_files --> graph_to_mermaid
    graph_to_mermaid_render_diagram_files --> graph_to_mermaid_generate_html_viewer
    graph_to_mermaid_render_diagram_cli --> graph_to_mermaid_render_diagram_files
    narrate_diff --> narrate_diff_format_diff_for_llm
    sample_package_app_AppService --> sample_package_base_BaseService
    sample_package_app_AppService --> sample_package_utils_format_message
    sample_package_app_AppService --> sample_package_utils_compute_total
    sample_package_app_main --> sample_package_app_AppService
    sample_package_app_main --> dev_server_run
    test_api_TestApiAnalyze --> api_analyze_parse_github_url
    test_api_TestApiAnalyze --> codebase_graph_build_graph_from_sources
    test_api_TestApiAnalyze --> api_analyze_fetch_repo_tree
    test_api_TestApiAnalyze --> api_analyze_handler
    test_api_TestApiAnalyze --> dev_server_run
    test_diff_TestDiffGraphsPure --> diff_graph_diff_graphs
    test_diff_TestGetGraphAtRevision --> diff_graph_get_graph_at_revision
    test_diff_TestEndToEndSamplePackageDiff --> diff_graph_get_graph_at_revision
    test_diff_TestEndToEndSamplePackageDiff --> diff_graph_diff_graphs
    test_diff_TestEndToEndSamplePackageDiff --> dev_server_run
    test_graph_TestCodebaseGraph --> codebase_graph_build_graph
    test_graph_TestCodebaseGraph --> dev_server_run
    test_narrate_TestNarrateDiff --> narrate_diff
    test_narrate_TestNarrateDiff --> narrate_diff_format_diff_for_llm
    test_narrate_TestNarrateDiff --> dev_server_run
    test_narrate_TestNarrateDiff --> sample_package_app_main
    test_render_TestGraphToMermaid --> graph_to_mermaid
    test_render_TestGraphToMermaid --> graph_to_mermaid_generate_html_viewer
    test_render_TestGraphToMermaid --> graph_to_mermaid_render_diagram_files
    test_render_TestGraphToMermaid --> dev_server_run
    test_render_TestGraphToMermaid --> graph_to_mermaid_count_rendered_edges
    test_render_TestGraphToMermaid --> graph_to_mermaid_count_rendered_nodes
    test_render_TestGraphToMermaid --> graph_to_mermaid_get_collapse_info

    %% Node Base Styling
    classDef default fill:#12161D,stroke:#232833,stroke-width:1px,color:#F2F1ED;

    %% Edge Styling by Type
    linkStyle 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45 stroke:#414957,stroke-width:1.5px;
    linkStyle 46 stroke:#4A5568,stroke-width:1.5px,stroke-dasharray:7 5;
    linkStyle 47,48,49,50,51,52,53,54,55,56,57,58,59,60,61 stroke:#4A5568,stroke-width:1.5px,stroke-dasharray:1 5;
    linkStyle 62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124 stroke:#414957,stroke-width:1px,opacity:0.55;
```

---

## How It Works (End-to-End)

```
GitHub / Local Repo ──> AST Parser ──> Structural Graph ──> LoD Filter ──> Interactive Studio Canvas
                             │                                    │
                             ├──> Git Revision Differ             └──> Groq AI Narration (openai/gpt-oss-120b)
```

1. **AST Analysis (`codebase_graph.py`)**: Traverses source files using Python's native `ast` module to extract modules, classes, inheritance hierarchies, import graphs, and call targets without executing user code.
2. **Level-of-Detail (LoD) Collapsing (`graph_to_mermaid.py`)**: Automatically prevents visual bloat on large codebases (>150 nodes) with intelligent two-tier collapsing:
   - *Tier 1*: Omits function nodes, badge-attributing counts to parent classes/modules.
   - *Tier 2*: Escalates to module-level view with combined class and function badges for very dense repositories (e.g. Pygments).
3. **Architecture Studio (`index.html`)**: Renders diagrams via Mermaid.js and ELK with pan/zoom canvas controls, fullscreen toggle, SVG export, and an overhead collapse indicator.
4. **Structural Git Differ (`diff_graph.py`)**: Computes semantic additions, removals, and modifications between git revisions (branches or commits).
5. **Architectural Narration (`narrate_diff.py`)**: Generates executive summaries of codebase structure and pull-request impact via Groq API (default model: `openai/gpt-oss-120b`).

---

## Tech Stack

- **Core Analysis**: Python (`ast`, `pathlib`, `collections`) — zero heavyweight parser dependencies
- **Visualization**: [Mermaid.js](https://mermaid.js.org/) with [ELK layout engine](https://www.eclipse.org/elk/) for clean orthogonal geometry
- **AI Engine**: [Groq API](https://groq.com/) running `openai/gpt-oss-120b`
- **Frontend**: Vanilla HTML5, CSS3 studio layout, SVG pan/zoom transform matrix
- **Cloud Runtime**: Vercel Serverless Python Function (`api/analyze.py`)
- **Cost**: 100% Free-Tier compatible (runs on free serverless and free Groq credits with zero database requirements).

---

## Quickstart & Local Setup

### 1. Clone & Install
```bash
git clone https://github.com/AaruneshAP/archgraph.git
cd archgraph
pip install -r requirements.txt
```

### 2. Environment Setup (Optional for AI Narration)
Create a `.env` file in the root directory:
```bash
GROQ_API_KEY="gsk_your_groq_api_key_here"
```

### 3. Run Locally

**Start the interactive web visualizer:**
```bash
python dev_server.py 3000
# Open http://localhost:3000 in your browser
```

**Or run the CLI to visualize any local directory:**
```bash
# Analyze this repo or any local project:
python codebase_graph.py . -o graph.json
python render_diagram.py graph.json

# Open the generated standalone viewer:
# Windows:
start graph.html
# macOS/Linux:
open graph.html
```

**Run Automated Tests:**
```bash
python -m unittest discover -p "test_*.py"
```

---

## License

MIT License. Free for open-source exploration and educational use.
