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
    LayerShell.Window.margins.left: Math.round(root.layerShellMarginLeft)
    LayerShell.Window.margins.top: Math.round(root.layerShellMarginTop)
    LayerShell.Window.margins.right: 0
    LayerShell.Window.margins.bottom: 0

    function setWaylandDragMargins(left, top) {
        const maxLeft = Math.max(0, Screen.width - root.width)
        const maxTop = Math.max(0, Screen.height - root.height)
        root.layerShellMarginLeft = Math.max(0, Math.min(maxLeft, left))
        root.layerShellMarginTop = Math.max(0, Math.min(maxTop, top))
    }

    // The generic DragHandler receives positions in window-local coordinates.
    // Moving a layer-surface by changing its margins changes those coordinates
    // underneath the active gesture, which can create a positive feedback jump.
    // This Wayland-only handle reconstructs the pointer in desktop coordinates
    // as current layer margin + local position before calculating the new margin.
    Item {
        id: waylandLogoDragHandle
        x: Math.round((root.width - width) / 2)
        y: 26
        width: 48
        height: 48
        z: 1000

        MouseArea {
            id: waylandLogoMouse
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            preventStealing: true
            cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor

            property real pressMarginLeft: 0
            property real pressMarginTop: 0
            property real pressDesktopX: 0
            property real pressDesktopY: 0
            property bool moved: false

            onPressed: (mouse) => {
                pressMarginLeft = root.layerShellMarginLeft
                pressMarginTop = root.layerShellMarginTop
                pressDesktopX = root.layerShellMarginLeft
                                + waylandLogoDragHandle.x + mouse.x
                pressDesktopY = root.layerShellMarginTop
                                + waylandLogoDragHandle.y + mouse.y
                moved = false
            }

            onPositionChanged: (mouse) => {
                if (!pressed)
                    return

                const currentDesktopX = root.layerShellMarginLeft
                                      + waylandLogoDragHandle.x + mouse.x
                const currentDesktopY = root.layerShellMarginTop
                                      + waylandLogoDragHandle.y + mouse.y
                const dx = currentDesktopX - pressDesktopX
                const dy = currentDesktopY - pressDesktopY

                if (!moved && Math.abs(dx) < 4 && Math.abs(dy) < 4)
                    return

                moved = true
                root.setWaylandDragMargins(pressMarginLeft + dx,
                                           pressMarginTop + dy)
            }

            onReleased: {
                const wasMoved = moved
                moved = false
                if (!wasMoved)
                    root.shellAdapter.minimize_to_floating()
            }

            onCanceled: moved = false
        }
    }
}
