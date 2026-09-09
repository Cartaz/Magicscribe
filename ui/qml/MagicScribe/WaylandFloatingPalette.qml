import QtQuick
import org.kde.layershell 1.0 as LayerShell

FloatingPalette {
    id: root

    layerShellPlacement: true

    LayerShell.Window.anchors: LayerShell.Window.AnchorTop
                               | LayerShell.Window.AnchorLeft
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone
    LayerShell.Window.scope: "magicscribe-floating"
    LayerShell.Window.margins: ({
        left: Math.round(root.layerShellMarginLeft),
        top: Math.round(root.layerShellMarginTop),
        right: 0,
        bottom: 0
    })
}
