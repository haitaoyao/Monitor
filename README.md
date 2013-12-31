Monitor
=======

Linux Host，MySQL，Oracle monitor tools

1.Script Abstract：
------------------
hmon.py: The script of monitoring Linux os system including cpu,memory,disk,net,file system at a regular interval.<br/>
mmon.py: The script of monitoring MySQL DataBase with innodb engine on Linux platform at a regular interval.<br/>
omon.py: The script of monitoring Oracle DataBase on Linux platform at a regular interval.<br/>
mon.sh:  The script of convenient way to retieve monitor [OS/MySQL/Oralce] Datas.<br/>
pidmon:  The script of monitor Linux process.


2.Deploy:
------------------
  1.deploy hmon.py:<br/>
    nohup /home/script/hmon.py >/dev/null 2>&1 &<br/>
  
  2.deploy mmon.py:<br/>
    nohup /home/script/mmon.py port >/dev/null 2>&1 &<br/>
  
  3.deploy omon.py:<br/>
    nohup /home/script/omon.py port >/dev/null 2>&1 &<br/>
  
3.Usage:<br/>
------------------
  mon key [value]:<br/>
  ----------------------------------------------------
  core:           --the brief monitor data with a few metrics on Linux OS<br/>
  cpu:            --the cpu monitor data<br/>
  mem:            --the memory monitor data<br/>
  net:            --the network monitor data<br/>
  fs:             --the file system monitor data<br/>
  disk:           --the disks system monitor data<br/>
  mysql           --the MySQL core monitor data<br/>
  mysql [plus]    --the MySQL plus monitor data<br/>
  oracle          --the Oracle monitor data<br/>
  oracle [plus]   --the Oracle plus monitor data<br/>
  pid [pidvalue]  --the linux process monitor <br/>

4.Metrics Interpret：
------------------
