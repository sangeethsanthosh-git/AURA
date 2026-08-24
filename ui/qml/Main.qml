import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    width: 1240
    height: 820
    minimumWidth: 960
    minimumHeight: 680
    visible: true
    title: "AURA ASUS"
    color: Theme.background

    Component.onCompleted: {
        auraBridge.messageReceived.connect(function(role, text, intent, source) {
            chatModel.append({ role: role, text: text, intent: intent, source: source })
        })
        auraBridge.errorOccurred.connect(function(message) {
            toastText.text = message
            toast.open()
        })
    }

    ListModel {
        id: chatModel
        ListElement {
            role: "aura"
            text: "I am here. The QML shell is ready while the local backend starts."
            intent: ""
            source: ""
        }
    }

    AppShell {
        anchors.fill: parent
        chatModel: chatModel
    }

    Popup {
        id: toast
        x: Math.round((window.width - width) / 2)
        y: 28
        width: Math.min(520, window.width - 48)
        modal: false
        focus: false
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle {
            radius: 14
            color: Theme.surface
            border.color: Theme.border
        }
        contentItem: Label {
            id: toastText
            color: Theme.textPrimary
            wrapMode: Text.WordWrap
            padding: 14
        }
        Timer {
            interval: 4200
            running: toast.visible
            onTriggered: toast.close()
        }
    }
}
