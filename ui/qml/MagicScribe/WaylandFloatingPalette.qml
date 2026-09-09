import QtQuick
import org.kde.layershell 1.0 as LayerShell

FloatingPalette {
    id: root

    layerShellPlacement: true
    flags: Qt.FramelessWindowHint

    LayerShell.Window.anchors: LayerShell.Window.AnchorTop
                               | LayerShell.Window.AnchorLeft
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone
    LayerShell.Window.scope: "magicscribe-floating"
    LayerShell.Window.margins.left: Math.round(root.layerShellMarginLeft)
    LayerShell.Window.margins.top: Math.round(root.layerShellMarginTop)
    LayerShell.Window.margins.right: 0
    LayerShell.Window.margins.bottom: 0
}
