import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    required property var chatModel

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 28
        spacing: 16

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 8
            model: root.chatModel
            delegate: ChatMessage {
                required property string role
                required property string text
                required property string intent
                required property string source

                messageRole: role
                messageText: text
                intent: intent
                source: source
            }
            onCountChanged: Qt.callLater(function() { list.positionViewAtEnd() })
        }

        ChatInput {
            Layout.fillWidth: true
            onSend: auraBridge.sendMessage(message)
        }
    }
}
