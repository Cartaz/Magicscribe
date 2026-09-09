import QtQuick
import org.kde.layershell 1.0 as LayerShell

ControlPanel {
    id: root

    layerShellPlacement: true

    LayerShell.Window.anchors: LayerShell.Window.AnchorTop
                               | LayerShell.Window.AnchorLeft
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityOnDemand
    LayerShell.Window.scope: "magicscribe-control"
    LayerShell.Window.margins: Qt.margins(
                                   Math.round(root.layerShellMarginLeft),
                                   Math.round(root.layerShellMarginTop),
                                   0,
                                   0
                               )
}
