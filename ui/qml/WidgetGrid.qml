import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

GridLayout {
    columns: width < 900 ? 1 : 4
    columnSpacing: 14
    rowSpacing: 14

    WidgetCard {
        Layout.columnSpan: parent.columns === 1 ? 1 : 2
        Layout.fillWidth: true
        title: "AURA Status"
        StatusPill { label: "Backend"; value: auraBridge.backendState }
        Label {
            Layout.fillWidth: true
            text: auraBridge.statusSummary
            color: Theme.textSecondary
            wrapMode: Text.WordWrap
        }
    }

    WidgetCard {
        Layout.columnSpan: parent.columns === 1 ? 1 : 2
        Layout.fillWidth: true
        title: "Memory"
        Label {
            Layout.fillWidth: true
            text: auraBridge.memoryCount === 0 ? "No active memories exposed." : auraBridge.memoryCount + " active memories."
            color: Theme.textSecondary
            wrapMode: Text.WordWrap
        }
    }

    WidgetCard {
        Layout.columnSpan: parent.columns === 1 ? 1 : 2
        Layout.fillWidth: true
        title: "Recent Activity"
        Label {
            Layout.fillWidth: true
            text: auraBridge.activityCount === 0 ? "No session activity yet." : auraBridge.activityCount + " activities recorded."
            color: Theme.textSecondary
            wrapMode: Text.WordWrap
        }
    }

    WidgetCard {
        Layout.fillWidth: true
        title: "Weather"
        Label {
            Layout.fillWidth: true
            text: "Ask for weather in chat. Dedicated weather widget data is not exposed yet."
            color: Theme.textSecondary
            wrapMode: Text.WordWrap
        }
    }

    WidgetCard {
        Layout.fillWidth: true
        title: "Vision"
        Label {
            Layout.fillWidth: true
            text: "OFF by default. Use screen requests in chat."
            color: Theme.textSecondary
            wrapMode: Text.WordWrap
        }
    }

    WidgetCard {
        Layout.fillWidth: true
        title: "Tasks"
        Label {
            Layout.fillWidth: true
            text: "No dedicated task store exposed. Hands actions work through chat."
            color: Theme.textSecondary
            wrapMode: Text.WordWrap
        }
    }
}
