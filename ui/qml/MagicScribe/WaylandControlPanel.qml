import QtQuick
import org.kde.layershell 1.0 as LayerShell

ControlPanel {
    id: root

    layerShellPlacement: true
    flags: Qt.FramelessWindowHint

    LayerShell.Window.anchors: LayerShell.Window.AnchorTop
                               | LayerShell.Window.AnchorLeft
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityOnDemand
    LayerShell.Window.scope: "magicscribe-control"
    LayerShell.Window.margins: ({
        left: Math.round(root.layerShellMarginLeft),
        top: Math.round(root.layerShellMarginTop),
        right: 0,
        bottom: 0
    })
}
