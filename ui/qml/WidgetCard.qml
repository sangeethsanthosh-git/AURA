import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    property string title: ""
    default property alias content: body.data

    radius: Theme.radiusMedium
    color: Theme.surface
    border.color: Theme.border
    implicitHeight: 154

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 10

        Label {
            text: root.title
            color: Theme.textPrimary
            font.bold: true
            font.pixelSize: 15
        }

        ColumnLayout {
            id: body
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 8
        }
    }
}
