import QtQuick
import org.kde.layershell 1.0 as LayerShell

FloatingPalette {
    id: root

    flags: Qt.FramelessWindowHint

    LayerShell.Window.anchors: LayerShell.Window.AnchorTop
                               | LayerShell.Window.AnchorBottom
                               | LayerShell.Window.AnchorLeft
                               | LayerShell.Window.AnchorRight
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone
    LayerShell.Window.scope: "magicscribe-floating"
    LayerShell.Window.margins.left: 0
    LayerShell.Window.margins.top: 0
    LayerShell.Window.margins.right: 0
    LayerShell.Window.margins.bottom: 0
}
