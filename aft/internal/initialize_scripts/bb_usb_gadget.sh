#!/bin/bash
# this file should be copied to "/usr/bin/bb_usb_gadget.sh"

# If no arguments given, use default support.img as mass storage emulation
# file. Otherwise use the given argument.
# https://www.kernel.org/doc/Documentation/usb/gadget_configfs.txt
if [ -z "$1" ]; then
    MASS_STORAGE_FILE="/root/support_image/support.img"
else
    MASS_STORAGE_FILE=$1
fi

set_up_gadget() {
    UDC=musb-hdrc.0 # USB Device Driver found in /sys/class/udc/

    # Gadget configuration
    GADGET_DIR='/config/usb_gadget/gadget'
    IDVENDOR='0x8086'
    IDPRODUCT='0xbeef'
    SERIALNUMBER='1.0'
    MANUFACTURER='Hailo'
    PRODUCT='Keyboard, mass storage and usb ethernet gadget'
    CONFIG_NAME='Config 1'
    MAX_POWER=120 # Maximum current to draw in mA

    # Standard HID keyboard configuration settings
    PROTOCOL=1
    SUBCLASS=1
    REPORT_LENGTH=8
    REPORT_DESC='\x05\x01\x09\x06\xa1\x01\x05\x07\x19\xe0\x29\xe7\x15\x00\x25\x01\x75\x01\x95\x08\x81\x02\x95\x01\x75\x08\x81\x03\x95\x05\x75\x01\x05\x08\x19\x01\x29\x05\x91\x02\x95\x01\x75\x03\x91\x03\x95\x06\x75\x08\x15\x00\x25\x65\x05\x07\x19\x00\x29\x65\x81\x00\xc0'

    echo "Start configfs"
    modprobe libcomposite
    mount none /config -t configfs

    echo "Make basic configuration directories"
    mkdir $GADGET_DIR
    cd $GADGET_DIR || exit
    mkdir strings/0x409
    mkdir configs/c.1
    mkdir configs/c.1/strings/0x409

    echo "Make directories for gadgets functions"
    mkdir functions/mass_storage.0
    mkdir functions/hid.usb0
    mkdir functions/ecm.usb0

    echo "Configure the gadget"
    echo $IDVENDOR >idVendor
    echo $IDPRODUCT >idProduct
    echo $SERIALNUMBER >strings/0x409/serialnumber
    echo $MANUFACTURER >strings/0x409/manufacturer
    echo $PRODUCT >strings/0x409/product
    echo $MAX_POWER >configs/c.1/MaxPower
    echo $CONFIG_NAME >configs/c.1/strings/0x409/configuration

    echo "Configure mass storage"
    echo "DONE in line 474 but need to change the image"
    echo "$MASS_STORAGE_FILE" >functions/mass_storage.0/lun.0/file
    ln -s functions/mass_storage.0 configs/c.1

    echo "Configure HID keyboard"
    echo $PROTOCOL >functions/hid.usb0/protocol
    echo $SUBCLASS >functions/hid.usb0/subclass
    echo $REPORT_LENGTH >functions/hid.usb0/report_length
    echo -ne $REPORT_DESC >functions/hid.usb0/report_desc
    ln -s functions/hid.usb0 configs/c.1

    echo "Configure USB ethernet"
    ln -s functions/ecm.usb0 configs/c.1

    echo "Start gadget"
    echo $UDC >UDC
}

set_up_gadget
