import QtQuick 2.15
import QtQuick.Layouts 1.12

import UI.Common.Controls.Buttons.Highlight 1.0 as HighlightButtons
import UI.Common.Dialogs 1.0 as Dialogs
import UI.Common.Controls.Inputs 1.0 as Inputs
import UI.Common.Styles.Text 1.0 as Styles
import UI.Common.Controls.Atoms 1.0 as Atoms
import UI.Assets.Icons 1.0
import UI.Values 1.0

Dialogs.BasicDialog {
    id: rootId
    dialogHeight: Dimensions.sizes.ultraLarge*3
    dialogWidth: Dimensions.sizes.huge*3

    property var controller

    //Really important to not leak memory
    onDialogClosed: controller.cleanup()

    title: "Greetings Dialog"
    titleIcon: Icons.normal.bubble

    contentComponent: Component {

        Item {
            anchors.fill: parent
            anchors.margins: Dimensions.margins.middle

            ColumnLayout {
                id: buttonLayoutId
                anchors.fill: parent

                Atoms.TextView {
                    id: labelId

                    style: Styles.BodyBoldTextStyle{}
                    text: "What is your name?"
                    horizontalAlignment: Text.AlignLeft

                    Layout.bottomMargin: Dimensions.margins.tiniest
                    Layout.fillWidth: true
                }

                Inputs.TextInput {
                    id: textInputId
                    text: "John Doe"
                    style: Styles.BodyTextStyle{}

                    Component.onCompleted: textInputId.forceActiveFocus()

                    Layout.fillWidth: true
                }

                HighlightButtons.SquareTextHighlightButton {
                    id: greetingsId
                    text: qsTr("Show Greetings")
                    enabled: true

                    Layout.topMargin: Dimensions.sizes.small
                    Layout.bottomMargin: Dimensions.margins.small

                    onClicked: {
                        controller.greetings(textInputId.text)
                        rootId.closeDialog()
                    }
                }
            }
        }
    }
}
