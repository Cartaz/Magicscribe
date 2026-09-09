import QtQuick
import org.kde.layershell 1.0 as LayerShell

Window {
    id: root

    visible: false
    color: "transparent"
    title: "MagicScribe Overlay"
    flags: Qt.FramelessWindowHint
           | Qt.Tool
           | Qt.WindowDoesNotAcceptFocus

    LayerShell.Window.anchors: LayerShell.Window.AnchorTop
                               | LayerShell.Window.AnchorBottom
                               | LayerShell.Window.AnchorLeft
                               | LayerShell.Window.AnchorRight
    LayerShell.Window.layer: LayerShell.Window.LayerTop
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone
    LayerShell.Window.scope: "magicscribe-overlay"
}
