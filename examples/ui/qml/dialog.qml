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
    dialogHeight: Dimensions.sizes.huge*2
    dialogWidth: Dimensions.sizes.huge*3

    // Our controller property that we set from python by calling createWithInitialProperties
    property var controller

    title: "Greetings Dialog"
    titleIcon: Icons.normal.bubble

    contentComponent: Component {

        Item {
            anchors.fill: parent
            anchors.margins: Dimensions.margins.middle

            // Similar to a QVBoxLayout
            ColumnLayout {
                anchors.fill: parent

                // The first entry in the column layout is a simple label.
                Atoms.TextView {
                    style: Styles.BodyBoldTextStyle{}
                    text: "What is your name?"
                    horizontalAlignment: Text.AlignLeft

                    Layout.bottomMargin: Dimensions.margins.tiniest
                    Layout.fillWidth: true
                }

                // The second entry is a text input field
                Inputs.TextInput {
                    // We set an ID so that we can access it later
                    id: textInputId

                    // Default text
                    text: "John Doe"
                    style: Styles.BodyTextStyle{}

                    // Set the focus to this object when the text input has loaded.
                    Component.onCompleted: textInputId.forceActiveFocus()

                    Layout.fillWidth: true
                }

                // Third, show a blue button to the user to trigger the greetings method
                HighlightButtons.SquareTextHighlightButton {
                    text: "Show Greetings"
                    hasBackground: true

                    Layout.topMargin: Dimensions.sizes.small
                    Layout.bottomMargin: Dimensions.margins.small

                    // JavaScript that is executed when the user clicks the button
                    onClicked: {
                        // First, we tell our python script that the button was clicked.
                        // By that we provide the current text from our TextView
                        controller.greetings(textInputId.text)

                        // Then we close this dialog
                        rootId.closeDialog()
                    }
                }
            }
        }
    }
}
