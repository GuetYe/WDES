#!/bin/bash
FileName="startup.sh"
rm /etc/init.d/$FileName
rm /etc/rc3.d/S01$FileName
rm /etc/rc4.d/S01$FileName
rm /etc/rc5.d/S01$FileName

sudo cp $FileName /etc/init.d/

sudo chmod +x /etc/init.d/$FileName

ln -s /etc/init.d/$FileName /etc/rc3.d/S01$FileName
ln -s /etc/init.d/$FileName /etc/rc4.d/S01$FileName
ln -s /etc/init.d/$FileName /etc/rc5.d/S01$FileName
