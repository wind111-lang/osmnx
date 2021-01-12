"""Create interactive Leaflet web maps of graphs and routes via folium."""

import json

from . import utils_graph

# folium is an optional dependency for the folium plotting functions
try:
    import folium
except ImportError:
    folium = None


def plot_graph_folium(
    G,
    graph_map=None,
    popup_attribute=None,
    tiles="cartodbpositron",
    zoom=1,
    fit_bounds=True,
    edge_color="#333333",
    edge_width=5,
    edge_opacity=1,
    **kwargs,
):
    """
    Plot a graph as an interactive Leaflet web map.

    Note that anything larger than a small city can produce a large web map
    file that is slow to render in your browser.

    Parameters
    ----------
    G : networkx.MultiDiGraph
        input graph
    graph_map : folium.folium.Map
        if not None, plot the graph on this preexisting folium map object
    popup_attribute : string
        edge attribute to display in a pop-up when an edge is clicked
    tiles : string
        name of a folium tileset
    zoom : int
        initial zoom level for the map
    fit_bounds : bool
        if True, fit the map to the boundaries of the graph's edges
    edge_color : string
        color of the edge lines
    edge_width : numeric
        width of the edge lines
    edge_opacity : numeric
        opacity of the edge lines
    kwargs : dict
        keyword arguments to pass to folium.PolyLine(), see folium docs for
        options (e.g. `color="#333333", weight=5, opacity=0.7`)

    Returns
    -------
    graph_map : folium.folium.Map
    """
    # create gdf of all graph edges
    gdf_edges = utils_graph.graph_to_gdfs(G, nodes=False)

    return _plot_folium(
        gdf_edges,
        graph_map,
        popup_attribute,
        tiles,
        zoom,
        fit_bounds,
        edge_color,
        edge_width,
        edge_opacity,
        **kwargs,
    )


def plot_route_folium(
    G,
    route,
    route_map=None,
    popup_attribute=None,
    tiles="cartodbpositron",
    zoom=1,
    fit_bounds=True,
    route_color="#cc0000",
    route_width=5,
    route_opacity=1,
    **kwargs,
):
    """
    Plot a route as an interactive Leaflet web map.

    Parameters
    ----------
    G : networkx.MultiDiGraph
        input graph
    route : list
        the route as a list of nodes
    route_map : folium.folium.Map
        if not None, plot the route on this preexisting folium map object
    popup_attribute : string
        edge attribute to display in a pop-up when an edge is clicked
    tiles : string
        name of a folium tileset
    zoom : int
        initial zoom level for the map
    fit_bounds : bool
        if True, fit the map to the boundaries of the route's edges
    route_color : string
        color of the route's line
    route_width : numeric
        width of the route's line
    route_opacity : numeric
        opacity of the route's line
    kwargs : dict
        keyword arguments to pass to folium.PolyLine(), see folium docs for
        options (e.g. `color="#cc0000", weight=5, opacity=0.7`)

    Returns
    -------
    route_map : folium.folium.Map
    """
    # create gdf of the route edges in order
    node_pairs = zip(route[:-1], route[1:])
    uvk = ((u, v, min(G[u][v], key=lambda k: G[u][v][k]["length"])) for u, v in node_pairs)
    gdf_edges = utils_graph.graph_to_gdfs(G.subgraph(route), nodes=False).loc[uvk]

    return _plot_folium(
        gdf_edges,
        route_map,
        popup_attribute,
        tiles,
        zoom,
        fit_bounds,
        route_color,
        route_width,
        route_opacity,
        **kwargs,
    )


def _plot_folium(
    gdf,
    m,
    popup_attribute,
    tiles,
    zoom,
    fit_bounds,
    color,
    weight,
    opacity,
    **kwargs,
):
    """
    Plot a GeoDataFrame of LineStrings on a folium map object.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        a GeoDataFrame of LineString geometries and attributes
    m : folium.folium.Map or folium.FeatureGroup
        if not None, plot on this preexisting folium map object
    popup_attribute : string
        attribute to display in pop-up on-click, if None, no popup
    tiles : string
        name of a folium tileset
    zoom : int
        initial zoom level for the map
    fit_bounds : bool
        if True, fit the map to gdf's boundaries
    color : string
        color of the lines
    weight : numeric
        width of the lines
    opacity : numeric
        opacity of the lines
    kwargs : dict
        keyword arguments to pass to folium.PolyLine()

    Returns
    -------
    m : folium.folium.Map
    """
    # check if we were able to import folium successfully
    if folium is None:
        raise ImportError("folium must be installed to use this optional feature")

    # get centroid
    x, y = gdf.unary_union.centroid.xy
    centroid = (y[0], x[0])

    # create the folium web map if one wasn't passed-in
    if m is None:
        m = folium.Map(location=centroid, zoom_start=zoom, tiles=tiles)

    # identify the geometry and popup columns
    if popup_attribute is None:
        attrs = ["geometry"]
    else:
        attrs = ["geometry", popup_attribute]

    # add each edge to the map
    for vals in gdf[attrs].values:
        params = dict(zip(["geom", "popup_val"], vals))
        pl = _make_folium_polyline(
            **params,
            color=color,
            weight=weight,
            opacity=opacity,
            **kwargs,
        )
        pl.add_to(m)

    # if fit_bounds is True, fit the map to the bounds of the route by passing
    # list of lat-lng points as [southwest, northeast]
    if fit_bounds and isinstance(m, folium.Map):
        tb = gdf.total_bounds
        m.fit_bounds([(tb[1], tb[0]), (tb[3], tb[2])])

    return m


def _make_folium_polyline(geom, color, weight, opacity, popup_val=None, **kwargs):
    """
    Turn LineString geometry into a folium PolyLine with attributes.

    Parameters
    ----------
    geom : shapely LineString
        geometry of the line
    color : string
        color of the line
    weight : numeric
        width of the line
    opacity : numeric
        opacity of the line
    popup_val : string
        text to display in pop-up when a line is clicked, if None, no popup
    kwargs : dict
        keyword arguments to pass to folium.PolyLine()

    Returns
    -------
    pl : folium.PolyLine
    """
    # locations is a list of points for the polyline folium takes coords in
    # lat,lng but geopandas provides them in lng,lat so we must reverse them
    locations = [(lat, lng) for lng, lat in geom.coords]

    # create popup if popup_val is not None
    if popup_val is None:
        popup = None
    else:
        # folium doesn't interpret html, so can't do newlines without iframe
        popup = folium.Popup(html=json.dumps(popup_val))

    # create a folium polyline with attributes
    pl = folium.PolyLine(
        locations=locations,
        popup=popup,
        color=color,
        weight=weight,
        opacity=opacity,
        **kwargs,
    )
    return pl
