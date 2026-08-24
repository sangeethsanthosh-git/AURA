import QtQuick
import QtQuick.Controls

Item {
    id: root
    required property string messageRole
    required property string messageText
    property string intent: ""
    property string source: ""

    width: ListView.view ? ListView.view.width : 600
    implicitHeight: bubble.implicitHeight + 10

    Rectangle {
        id: bubble
        width: Math.min(root.width * 0.78, 720)
        x: root.messageRole === "user" ? root.width - width - 4 : 4
        radius: 20
        color: root.messageRole === "user" ? "#dff1fb" : Theme.surface
        border.color: Theme.border
        implicitHeight: content.implicitHeight + 24

        Column {
            id: content
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 14
            spacing: 8

            Label {
                width: parent.width
                text: root.messageText
                color: Theme.textPrimary
                wrapMode: Text.WordWrap
                font.pixelSize: 14
            }

            Label {
                visible: root.intent.length > 0 || root.source.length > 0
                width: parent.width
                text: [root.intent, root.source].filter(function(x) { return x.length > 0 }).join(" - ")
                color: Theme.textMuted
                wrapMode: Text.WordWrap
                font.pixelSize: 11
            }
        }
    }
}
