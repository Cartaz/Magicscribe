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

    // MouseArea exposes only window-local x/y. Updating layer-shell margins while
    // using those coordinates feeds the compositor move back into the gesture.
    // QtWayland already tracks QMouseEvent.globalPosition() in QCursor::pos(), so
    // use only global pointer coordinates for the duration of the drag.
    Item {
        id: waylandLogoDragHandle
        x: Math.round((root.width - width) / 2)
        y: 26
        width: 48
        height: 48
        z: 1000

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            preventStealing: true
            cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor

            property real pressMarginLeft: 0
            property real pressMarginTop: 0
            property real pressGlobalX: 0
            property real pressGlobalY: 0
            property bool moved: false

            onPressed: {
                const cursor = root.shellAdapter.global_cursor_position()
                pressMarginLeft = root.layerShellMarginLeft
                pressMarginTop = root.layerShellMarginTop
                pressGlobalX = cursor.x
                pressGlobalY = cursor.y
                moved = false
            }

            onPositionChanged: {
                if (!pressed)
                    return

                const cursor = root.shellAdapter.global_cursor_position()
                const dx = cursor.x - pressGlobalX
                const dy = cursor.y - pressGlobalY

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
