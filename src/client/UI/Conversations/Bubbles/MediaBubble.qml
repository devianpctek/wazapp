// import QtQuick 1.0 // to target S60 5th Edition or Maemo 5
import QtQuick 1.1
import com.nokia.meego 1.0

import "../../common"

SpeechBubble {

    id:mediaBubble


    property string message;
    property string thumb;
    property int progress:0
    property variant media;


    property string transferState;

	property bool loaded: false

    signal downloadClicked()
    signal uploadClicked()

    function progressUpdated(progress){
        progressBar.value=progress
    }




    Component.onCompleted: {

		loaded = true


        switch(media.mediatype_id){
            case 2: {
				thumb = !media.local_path ? "data:image/jpg;base64,"+media.preview : "file://"+media.local_path
				openButton.text = message=="" ? qsTr("Image") : message
				break
			}
            case 3: {
				thumb = "image://theme/icon-m-content-audio"
				openButton.text = message=="" ? qsTr("Audio") : message
				break
			}
            case 4: {
				thumb = "image://theme/icon-m-content-videos"
				openButton.text = message=="" ? qsTr("Video") : message
				break
			}
            case 5: {
				thumb = media.preview ? "data:image/jpg;base64,"+media.preview : 
						"../common/images/content-location.png"
				transferState = "success"
				openButton.text = message=="" ? qsTr("Location") : message
				break
			}
            case 6: {
				thumb = media.preview ? "data:image/jpg;base64,"+media.preview : 
						"image://theme/icon-m-content-avatar-placeholder"
				transferState = "success"
				openButton.text = message
				break
			}
        }





        //msg_image = thumb
    }


//download,open,retry

	childrenWidth: realContainer.width

    bubbleContent: Rectangle {

        id:realContainer
        width: (state=="success" ? openButton.paintedWidth : 180) + 66
        height: state=="success" ? 54 + (openButton.lineCount==2? 32:0) : 80
        color:"transparent"
		anchors.left: parent.left
		anchors.leftMargin: from_me==1 ? 0 : (appWindow.inPortrait?480:854) -(openButton.visible?openButton.paintedWidth:180) - 86
       // height:parent.height
        state:(mediaBubble.progress > 0 && mediaBubble.progress < 100)?"inprogress": mediaBubble.transferState
		
        states: [

            State {
                name: "init"
                PropertyChanges {
                    target: progressBar
                    visible:true
                }

                PropertyChanges {
                    target: operationButton
                    visible: delegateContainer.from_me!=1
                    enabled:true
                    text: delegateContainer.from_me==1? qsTr("Send"):qsTr("Download")
                }
            },


            State {
                name: "success"
                PropertyChanges {
                    target: progressBar
                    visible: false
                }

                PropertyChanges {
                    target: openButton
                    visible:true
                }

                PropertyChanges {
                    target: operationButton
                    visible:false
                }

            },

            State {
                name: "inprogress"

                PropertyChanges {
                    target: progressBar
                    visible:true
                }

                PropertyChanges{
                    target: operationButton
                    enabled:false
                    visible:true
                    text: delegateContainer.from_me==1? qsTr("Sending"):qsTr("Downloading")
                }


            },

            State {
                name: "failed"
                PropertyChanges {
                    target: progressBar
                    visible:false
                }
                PropertyChanges {
                    target: operationButton
                    visible:true
                    enabled:true
                    text: qsTr("Retry")
                }
            }

        ]

		RoundedImage {
			id: mmsimage
			width: istate=="Loaded!" ? 66 : 0 
			size: istate=="Loaded!" ? 60 : 0
			height: width
			x: from_me==1 ? 18 : parent.width - 58
			y: name==="" ? -1 : name=="" ? - 22 : -29
            visible: thumb!=""
            imgsource: thumb
		}

        Item{
            id:buttonsHolder

            width: openButton.visible? openButton.paintedWidth : 180
            height:openButton.height
           // anchors.verticalCenter: msg_image.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: 66

            Text {
                id: openButton
                visible: state=="success"
                width: (appWindow.inPortrait ? 300 : 674)
				font.family: "Nokia Pure Light"
				font.weight: Font.Light
				font.pixelSize: 23
				color: from_me==1? "black" : "white"
                text: message
				maximumLineCount: 2
				anchors.left: from_me==1 ? parent.left : this.left
				anchors.right: from_me? this.right : parent.right
				anchors.leftMargin: from_me==1? 84 : 0
				wrapMode: "WrapAtWordBoundaryOrAnywhere"
				elide: Text.ElideRight
				horizontalAlignment: from_me==1? Text.AlignLeft : Text.AlignRight
            }

            Button {
                id: operationButton
                visible:false

                width: parent.width
                height: 38
                font.pixelSize: 20
                text: qsTr("Download")

                onClicked: {
                     operationButton.enabled=false
                    operationButton.text= qsTr("Initializing")

                    if(delegateContainer.from_me==1)
                        uploadClicked()
                    else
                        downloadClicked()


                }


            }

        }

        ProgressBar {
            id: progressBar
            minimumValue: 0
            maximumValue: 100
            value:progress
            width: buttonsHolder.width
            anchors.left: buttonsHolder.left
            anchors.top:buttonsHolder.bottom
            anchors.topMargin: 10
			visible: state!="success"

        }


    }

}
