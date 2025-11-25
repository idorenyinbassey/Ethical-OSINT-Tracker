import reflex as rx
from app.components.layout import sidebar, header
from app.states.auth_state import AuthState
from app.states.threat_map_state import ThreatMapState

def threat_map_page() -> rx.Component:
    leaflet_css = rx.el.link(rel="stylesheet", href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css")
    leaflet_js = rx.el.script(src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js")

    # Inline script to initialize the map and render markers from a JSON blob
    init_script = rx.el.script(
        """
        (function(){
          function ready(fn){ if(document.readyState!='loading'){fn()} else {document.addEventListener('DOMContentLoaded', fn)} }
          ready(function(){
            var el = document.getElementById('threat-markers-json');
            if(!el) return;
            var markers = [];
            try { markers = JSON.parse(el.textContent || '[]'); } catch(e) { markers = []; }
            var mapEl = document.getElementById('threat-map');
            if(!mapEl) return;
            if(!window.__threatMap){
              window.__threatMap = L.map(mapEl).setView([20,0], 2);
              L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 18, attribution: '&copy; OpenStreetMap'}).addTo(window.__threatMap);
            }
            if(window.__threatLayer){ window.__threatMap.removeLayer(window.__threatLayer); }
            var group = L.layerGroup();
            markers.forEach(function(m){
              var color = m.severity==='high' ? 'red' : (m.severity==='medium' ? 'orange' : 'green');
              var marker = L.circleMarker([m.lat, m.lon], {radius:6, color: color, fillColor: color, fillOpacity:0.7});
              var label = '<b>'+m.ip+'</b><br/>' + (m.city||'') + (m.country? ', '+m.country:'') + '<br/>' + (m.asn||'') + ' ' + (m.org||'');
              marker.bindPopup(label);
              group.addLayer(marker);
            });
            window.__threatLayer = group.addTo(window.__threatMap);
          });
        })();
        """
    )

    # Use rx.Var.to_string() to serialize the markers list to JSON
    markers_json = rx.el.script(
        ThreatMapState.threat_markers.to_string(),
        id="threat-markers-json",
        type="application/json"
    )

    map_container = rx.el.div(id="threat-map", class_name="w-full h-[600px] rounded-xl border border-gray-200 bg-white")

    return rx.cond(
        AuthState.is_authenticated,
        rx.el.div(
            sidebar(active_item="Threat Map"),
            rx.el.main(
                header(),
                rx.el.div(
                    rx.el.h1("Threat Map", class_name="text-2xl font-bold text-gray-900 mb-4"),
                    rx.el.div(
                        rx.el.div(
                            rx.el.button(
                                rx.cond(ThreatMapState.is_loading, rx.spinner(size="1"), "Refresh"),
                                on_click=ThreatMapState.load_threat_map,
                                class_name="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-sm font-medium"
                            ),
                            class_name="flex items-center gap-2 mb-4"
                        ),
                        leaflet_css,
                        leaflet_js,
                        markers_json,
                        map_container,
                        init_script,
                        class_name="p-4 bg-white rounded-xl border border-gray-200"
                    ),
                    on_mount=ThreatMapState.load_threat_map,
                    class_name="p-6 lg:p-8 max-w-[1600px] mx-auto"
                ),
                class_name="flex-1 lg:ml-72 bg-gray-50 min-h-screen font-['Raleway']"
            ),
            class_name="flex min-h-screen bg-gray-50"
        ),
        rx.el.div(
            rx.el.p("Login required", class_name="text-sm"),
            class_name="p-6"
        )
    )
