Monitor
=======

Linux Host，MySQL，Oracle monitor tools

1.Script Abstract：
------------------
	hmon.py: monitor Linux os system including cpu,memory,disk,net,file system at a regular interval.
	mmon.py: monitor MySQL DataBase with innodb engine on Linux platform at a regular interval.
	omon.py: monitor Oracle DataBase on Linux platform at a regular interval.
	mon.sh:  convenient way to retieve monitor [OS/MySQL/Oralce] Datas.
	pidmon:  monitor Linux process.


2.Deploy:
------------------
	1.deploy hmon.py:
		nohup /home/script/hmon.py >/dev/null 2>&1 &
	
	2.deploy mmon.py:
		nohup /home/script/mmon.py $PORT >/dev/null 2>&1 &
	
	3.deploy omon.py:
		nohup /home/script/omon.py >/dev/null 2>&1 &
	
3.Usage:
------------------
	mon key [value]:
	----------------------------------------------------
	core:           --the brief monitor data with a few metrics on Linux OS
	cpu:            --the cpu monitor data
	mem:            --the memory monitor data
	net:            --the network monitor data
	fs:             --the file system monitor data
	disk:           --the disks system monitor data
	mysql           --the MySQL core monitor data
	mysql [plus]    --the MySQL plus monitor data
	oracle          --the Oracle monitor data
	oracle [plus]   --the Oracle plus monitor data
	pid [pidvalue]  --the linux process monitor 

4.Metrics Interpret：
------------------
	Host monitor metrics:

	MySQL monitor metrics:

	Oracle monitor metrics:


5.Others:
------------------
