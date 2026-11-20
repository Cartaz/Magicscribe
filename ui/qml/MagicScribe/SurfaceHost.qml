import QtQuick

// Area interattiva dentro una surface fullscreen: la surface resta ferma, si
// muove solo questo host. Lo mantiene dentro la surface e comunica la sua
// geometria come input region, così il resto della surface resta click-through.
Item {
    id: host

    required property Window surface

    signal inputRegionRequested(real regionX, real regionY, real regionWidth, real regionHeight)

    // surface e' null mentre il componente viene costruito (x/y iniziali).
    function clampToSurface() {
        if (!host.surface)
            return
        host.x = Math.max(0, Math.min(host.surface.width - host.width, host.x))
        host.y = Math.max(0, Math.min(host.surface.height - host.height, host.y))
    }

    function syncInputRegion() {
        if (host.surface && host.surface.visible)
            host.inputRegionRequested(host.x, host.y, host.width, host.height)
    }

    onXChanged: syncInputRegion()
    onYChanged: syncInputRegion()
    onWidthChanged: syncInputRegion()
    onHeightChanged: syncInputRegion()

    Connections {
        target: host.surface

        // Nessun clamp alla comparsa: il restore 1:1 della toolbar puo'
        // posizionarla parzialmente fuori dalla surface (vedi FloatingPalette).
        function onVisibleChanged() {
            host.syncInputRegion()
        }

        function onWidthChanged() {
            host.clampToSurface()
            host.syncInputRegion()
        }

        function onHeightChanged() {
            host.clampToSurface()
            host.syncInputRegion()
        }
    }
}
