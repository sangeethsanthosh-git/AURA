import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    required property string label
    required property string value

    implicitWidth: content.implicitWidth + 22
    implicitHeight: 30
    radius: 15
    color: Theme.surface
    border.color: Theme.border

    RowLayout {
        id: content
        anchors.centerIn: parent
        spacing: 7

        Rectangle {
            Layout.preferredWidth: 7
            Layout.preferredHeight: 7
            radius: 4
            color: value === "READY" ? Theme.success : value === "ERROR" || value === "OFFLINE" ? Theme.danger : Theme.warning
        }

        Label {
            text: label + ": " + value
            color: Theme.textSecondary
            font.pixelSize: 12
        }
    }
}
