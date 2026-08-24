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
            title: "Activity"
            Label {
                Layout.fillWidth: true
                text: auraBridge.activityCount === 0 ? "Activity will appear after your first AURA request." : auraBridge.activityCount + " recent AURA activities this session."
                color: Theme.textSecondary
                wrapMode: Text.WordWrap
            }
        }
    }
}
