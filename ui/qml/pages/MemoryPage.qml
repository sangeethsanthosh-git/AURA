import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

ScrollView {
    id: root
    contentWidth: availableWidth

    ColumnLayout {
        width: root.availableWidth
        anchors.margins: 28

        WidgetCard {
            Layout.fillWidth: true
            title: "Memory"
            Label {
                Layout.fillWidth: true
                text: auraBridge.memoryCount === 0 ? "No active long-term memories are exposed yet." : auraBridge.memoryCount + " active local memories."
                color: Theme.textSecondary
                wrapMode: Text.WordWrap
            }
        }
    }
}
