import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property string title: ""
    property string message: ""

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28

        WidgetCard {
            Layout.fillWidth: true
            title: root.title
            Label {
                Layout.fillWidth: true
                text: root.message
                color: Theme.textSecondary
                wrapMode: Text.WordWrap
            }
        }
        Item { Layout.fillHeight: true }
    }
}
