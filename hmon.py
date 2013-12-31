#!/usr/bin/python
#Requirment:
#	python version > 2.2
#	kernel > 2.6.18
#	Directory:/home/admin/	
#
#

import sys,os 
import fcntl
import time
import re
import copy
import socket
import struct
import array
from datetime import datetime

VERSION 	= '0.1'
DIRMON  	= '/home/oracle/admin/'
INTERVAL	= 2
LOOP        = 0
HOST_CORE 	= 'host_core.log'
HOST_RAW 	= 'host_raw.log'
HOST_CPU	= 'host_cpu.log'
HOST_MEM 	= 'host_mem.log'
HOST_NET 	= 'host_net.log'
HOST_DISK 	= 'host_disk.log'
HOST_FS 	= 'host_fs.log'
HOST_FLK 	= '.host_lock.flk'
MAXSIZE		= 52428800

def chkEnv():
    global pyvers,knvers

    pyvers = sys.version_info
    knvers = os.uname()
    if pyvers < (2,2):
        print >>sys.stderr,"Error: Python 2.2 or later required!"
        sys.exit(1)
    if knvers[2] < '2.6':
        print >>sys.stderr,"Error: Linux kernel 2.6 or later required!"
        sys.exit(1)

def _init_path(path):
    try:
        if not os.path.exists(path):
            os.mkdir(path)
            sys.path.append(path)
    except Exception,e:
        print >>sys.stderr,"Error: " +str(e)
        sys.exit(1)

def _init_flock():
	global fd_flk

	try:
		fd_flk	= os.open(DIRMON+HOST_FLK,os.O_CREAT|os.O_WRONLY)
		fcntl.lockf(fd_flk,fcntl.LOCK_EX|fcntl.LOCK_NB)
	except IOError,e:
		print >>sys.stderr,"warn: " +str(e)
		try:
			fcntl.lockf(fd_flk,fcntl.LOCK_UN)
			os.close(fd_flk)
		except Exception,e:
			print >>sys.stderr,"Warn: " +str(e)
		sys.exit(0)

#init the log file description,and set buffersize
def _init_fd():
	global fh_core,fh_raw,fh_cpu,fh_mem,fh_disk,fh_fs,fh_net
	global fh_arr,fl_arr
	try:
		fh_core	= os.fdopen(os.open(DIRMON+HOST_CORE,os.O_RDWR|os.O_APPEND|os.O_CREAT),'a+',512)
		fh_raw	= os.fdopen(os.open(DIRMON+HOST_RAW,os.O_RDWR|os.O_APPEND|os.O_CREAT),'a+',512)
		fh_cpu	= os.fdopen(os.open(DIRMON+HOST_CPU,os.O_RDWR|os.O_APPEND|os.O_CREAT),'a+',512)
		fh_mem	= os.fdopen(os.open(DIRMON+HOST_MEM,os.O_RDWR|os.O_APPEND|os.O_CREAT),'a+',512)
		fh_disk	= os.fdopen(os.open(DIRMON+HOST_DISK,os.O_RDWR|os.O_APPEND|os.O_CREAT),'a+',512)
		fh_fs	= os.fdopen(os.open(DIRMON+HOST_FS,os.O_RDWR|os.O_APPEND|os.O_CREAT),'a+',512)
		fh_net	= os.fdopen(os.open(DIRMON+HOST_NET,os.O_RDWR|os.O_APPEND|os.O_CREAT),'a+',512)
		fh_arr	= [fh_core,fh_raw,fh_cpu,fh_mem,fh_disk,fh_fs,fh_net]
		fl_arr	= [DIRMON+HOST_CORE,DIRMON+HOST_RAW,DIRMON+HOST_CPU,DIRMON+HOST_MEM,DIRMON+HOST_DISK,DIRMON+HOST_FS,DIRMON+HOST_NET]
	except Exception,e:
		print >>sys.stderr,"Error: " +str(e)
		sys.exit(1)


def copyFile():
	try:
		statinfo	= os.stat(DIRMON+HOST_CORE)
		if (statinfo.st_size > MAXSIZE):
			_mvfile()
			_init_fd()
	except Exception, e:
		print >>sys.stderr,"Error: " +str(e)
		sys.exit(1)	

def _mvfile():
	global	fh_arr,fl_arr 
	try:	
		for fh in fh_arr:
			fh.close()
		for fl in fl_arr:
			try:
				os.unlink(fl+"_3")
			except:
				None
			try:
				os.rename(fl+"_2",fl+"_3")
			except:
				None
			try:
				os.rename(fl+"_1",fl+"_2")
			except:
				None
			try:
				os.rename(fl,fl+"_1")
			except:
				None
	except Exception, e:
		print >>sys.stderr,"Error: " +str(e)
		sys.exit(1)

def _destory():
		global fh_arr
		try:
			for fh in fh_arr:
				fh.close()
			fcntl.lockf(fd_flk,fcntl.LOCK_UN)
			os.close(fd_flk)	
		except Exception,e:
			print >>sys.stderr,"Error: "+str(e)
			sys.exit(1)

def _init_globalVar():
	global cpuCnt,spPattern,dPattern,netPattern,loadPattern
	cpuCnt		= 0
	try:
		for cpu in os.listdir("/sys/devices/system/cpu"):
			if cpu.startswith("cpu"):
				cpuCnt += 1
	except Exception,e:
		print >>sys.stderr,"Error: "+str(e)
		sys.exit(1)
	spPattern	=re.compile("\s+")
	dPattern	=re.compile("\d+:")
	netPattern	=re.compile("\s+|:[\s\t]*|\t+")
	loadPattern	=re.compile("\s+|/")

def _init_disk():
	global arr_mnt, arr_device,fio
	fio     = "fio" 
	arr_mnt	= []
	for mnt	in _readAll("/proc/mounts"):
		arr	= spPattern.split(mnt.strip("\n "))
		if arr[0].startswith("/dev/"):
			arr_mnt.append(arr[0][5:len(arr[0])])

	
	arr_device	=[]
	for device in os.listdir("/sys/block"):
		if device.startswith("cciss"):
			part    = device.replace("!","/")
		else:
			part    = device
		if part.startswith(fio):
			arr_device.append(device)
			continue
		for mnt in arr_mnt:
			if mnt.startswith(part):
				arr_device.append(device)
				break
	arr_device.sort()
	if(len(arr_device)>3):
	    arr_device  =arr_device[0:3]
	
	global disk_domain,disk_title,disk_width,disk_visible,disk_unit,disk_cut,disk_delimiter,disk_quantity
	disk_domain	=[]
	disk_title  =[]
	disk_width	=[]
	disk_visible=[]
	disk_unit	=[]
	disk_cut	=[]
	disk_delimiter=[]
	
	tt	=	["RD","RDz","RDt","WR","WRz","WRt"]
	disk_quantity	= len(arr_device)*8 + len(tt)
	
	for device	in arr_device:
		lat_device	= device[len(device)-1:len(device)]
		disk_domain.extend(['disk','disk','disk','disk','disk','disk','disk','disk'])	
		disk_title.extend([lat_device+"RD",lat_device+"RDz",lat_device+"RDt",lat_device+"WR",lat_device+"WRz",lat_device+"WRt",lat_device+"Ut",lat_device+"Qu"])
		disk_width.extend([4,4,4,4,4,4,3,3])
		disk_visible.extend([2,2,2,2,2,2,2,2])
		disk_cut.extend([False,False,False,False,False,False,False,False])
		disk_delimiter.extend([" "," "," "," "," "," "," ","|"])
		disk_unit.extend([3,4,1,3,4,1,1,1])
	

	disk_domain.extend(['disk','disk','disk','disk','disk','disk'])
	disk_title.extend(tt)
	disk_width.extend([4,4,4,4,4,4])
	disk_visible.extend([3,3,3,3,3,3])
	disk_cut.extend([False,False,False,False,False,False])
	disk_delimiter.extend([" "," "," "," "," ","|"])
	disk_unit.extend([3,4,1,3,4,1])

def _getMainDevice():
        arr_line        =_readAll("/proc/cpuinfo")
        var1    =32                 
        var2    =32
        for line in arr_line:
                if line.startswith("flags"):
                        arr     =spPattern.split(line)
                        if "lm" in arr:
                                var1    =40
                                var2    =16
        max_possible = 128  # arbitrary. raise if needed.
        bytes = max_possible * 32
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        names = array.array('B', '\0' * bytes)
        outbytes = struct.unpack('iL', fcntl.ioctl(
        s.fileno(),
        0x8912,  # SIOCGIFCONF
        struct.pack('iL', bytes, names.buffer_info()[0])
    ))[0]
        namestr = names.tostring()
        for i in range(0, outbytes, var1):
                name = namestr[i:i+var2].split('\0', 1)[0]
                if(name !="lo" and name !=""):
                        return name
        return False

def _init_net():
	global	bond, arr_eth
	bond    = ""
	arr_eth	= []
	try:
	    files	= os.listdir("/proc/net/bonding/")
	    if len(files)>0:
		    bond	= files[0]
		    for item in _readAll("/proc/net/bonding/" + bond):
			    arr     = item.strip("\n ").split(":")
			    if arr[0].startswith("Slave Interface"):
				    arr_eth.append(arr[1].strip(" "))
	except Exception,e:
		None

	global net_domain,net_title,net_width,net_visible,net_unit,net_cut,net_delimiter,net_quantity
	net_domain =[]
	net_title  =[]
	net_width  =[]
	net_visible=[]
	net_unit   =[]
	net_cut    =[]
	net_delimiter=[]

	tt  =   ["RV","RVz","RVe","TM","TMz","TMe"]
	net_quantity   = len(arr_eth) * len(tt)

	for device  in arr_eth:
		lat_device  = device[len(device)-1:len(device)]
		net_domain.extend(['net','net','net','net','net','net'])
		net_title.extend([lat_device+"RV",lat_device+"RVz",lat_device+"RVe",lat_device+"TM",lat_device+"TMz",lat_device+"TMe"])
		net_width.extend([4,4,4,4,4,4])
		net_visible.extend([2,2,2,2,2,2])
		net_cut.extend([False,False,False,False,False,False])
		net_delimiter.extend([" "," "," "," "," ","|"])
		net_unit.extend([3,4,3,3,4,3])

	main_device = _getMainDevice()
	if(main_device):
		if(bond ==""):
		    bond    =main_device
		net_quantity    += len(tt)
		net_domain.extend(['net','net','net','net','net','net'])
		net_title.extend(tt)
		net_width.extend([4,4,4,4,4,4])
		net_visible.extend([0,0,0,0,0,0])
		net_cut.extend([False,False,False,False,False,False])
		net_delimiter.extend([" "," "," "," "," ","|"])
		net_unit.extend([3,4,3,3,4,3])


def initEnv():
    #int the monitor directry  
	_init_path(DIRMON)
	#get excusive lock
	_init_flock()
	#init the log file description
	_init_fd()

	#calculate the cpu count
	_init_globalVar()
	
	#init the disk configiration
	_init_disk()
	
	#init the network device
	_init_net()
	
	#init display class for cpu,mem,net,disk,fs and so on	
	_init_disps()

def loopMon():
	_mon_time()
	_mon_load()
	_mon_cpu()
	_mon_irq()
	_mon_mem()
	_mon_mstat()
	_mon_disk()
	_mon_net()
	_mon_file()
	
def loopDisp():
    global rawValue,dispValue
    for disp in arrDisp:
        for i in range(disp.getQuantity()):
#           print disp.getDelta()
#           print disp
            rawValue    = disp.getDelta()[i]
            dispValue   = formatValue(rawValue,disp.getCut()[i],disp.getWidth()[i],disp.getUnit()[i])
            visible = disp.getVisible()[i]
            domain  = disp.getDomain()[i]
            width   = disp.getWidth()[i]
            delim   = disp.getDelim()[i]
            if visible in (0,3):
                fh_core.write(formatWidth(width) % (dispValue))
                fh_core.write(delim)
            if visible in (0,1,3):
                fh_raw.write(str(rawValue))
                fh_raw.write(",")
            if visible in (0,1,2):
                if domain in ('all','cpu'):
                    fh_cpu.write(formatWidth(width) % (dispValue))
                    fh_cpu.write(delim)
                if domain in ('all','mem'):
                    fh_mem.write(formatWidth(width) % (dispValue))
                    fh_mem.write(delim)
                if domain in ('all','disk'):
                    fh_disk.write(formatWidth(width) % (dispValue))
                    fh_disk.write(delim)
                if domain in ('all','net'):
                    fh_net.write(formatWidth(width) % (dispValue))
                    fh_net.write(delim)
                if domain in ('all','fs'):
                    fh_fs.write(formatWidth(width) % (dispValue))
                    fh_fs.write(delim)
    endLine()
	
def formatValue(rawValue,cut,width,unit):
	if cut:
		return rawValue[len(rawValue)-int(width):len(rawValue)]
	if unit == 1:
		rawIntValue = int(rawValue)
		if rawIntValue<1000:
			return rawValue
		elif rawIntValue >=1000 and rawIntValue <1000000:
			return str(rawIntValue/1000)+"K"
		elif rawIntValue>=1000000:
			return str(rawIntValue/1000000)+"M"
	if unit == 3:
		rawIntValue = int(rawValue)
		if rawIntValue<10000:
			return rawValue
		elif rawIntValue>=10000 and rawIntValue<1000000:
			return str(rawIntValue/1000)+"K"
		elif rawIntValue>=1000000:
			return str(rawIntValue/1000000)+"M"
	if unit == 4:
		rawIntValue = int(rawValue)
		if rawIntValue<10000:
			return rawValue
		elif rawIntValue>=10000 and rawIntValue<1024000:
			return str(rawIntValue/1024)+"K"
		elif rawIntValue>=1024000 and rawIntValue< 1048576:
			return str(float("%.1f" %(rawIntValue/1024.0/1024.0)))+"M"
		elif rawIntValue>= 1048576 and rawIntValue < 1048576000:
			return str(rawIntValue/1024/1024)+"M"
		elif rawIntValue >= 1048576000 and rawIntValue< 1073741824:
			return str(float("%.1f" %(rawIntValue/1024.0/1024.0/1024.0)))+"G"
		elif rawIntValue>=1073741824:
			return str(rawIntValue/1024/1024/1024)+"G"
	return rawValue

def formatWidth(width):
	return "%"+str(width)+"s"

def loopTitle():
	global title
	for disp in arrDisp:
		for i in range(disp.getQuantity()):
			title	= disp.getTitle()[i]
			if disp.getVisible()[i] in (0,3):
				fh_core.write(formatWidth(disp.getWidth()[i]) % (title))
				fh_core.write(disp.getDelim()[i])
			if disp.getVisible()[i] in (0,1,3):
				fh_raw.write(title)
				fh_raw.write(",")
			if disp.getVisible()[i] in (0,1,2):
				if disp.getDomain()[i] in ('all','cpu'):
					fh_cpu.write(formatWidth(disp.getWidth()[i]) % (title))
					fh_cpu.write(disp.getDelim()[i])
				if disp.getDomain()[i] in ('all','mem'):
					fh_mem.write(formatWidth(disp.getWidth()[i]) % (title))
					fh_mem.write(disp.getDelim()[i])
				if disp.getDomain()[i] in ('all','disk'):
					fh_disk.write(formatWidth(disp.getWidth()[i]) % (title))
					fh_disk.write(disp.getDelim()[i])
				if disp.getDomain()[i] in ('all','net'):
					fh_net.write(formatWidth(disp.getWidth()[i]) % (title))
					fh_net.write(disp.getDelim()[i])
				if disp.getDomain()[i] in ('all','fs'):
					fh_fs.write(formatWidth(disp.getWidth()[i]) % (title))			
					fh_fs.write(disp.getDelim()[i])			

	endLine()

def endLine():
    fh_core.write("\n")
    fh_raw.write("\n")
    fh_cpu.write("\n")
    fh_mem.write("\n")
    fh_disk.write("\n")
    fh_fs.write("\n")
    fh_net.write("\n")

    fh_core.flush()
    fh_raw.flush()
    fh_cpu.flush()
    fh_mem.flush()
    fh_disk.flush()
    fh_fs.flush()
    fh_net.flush()

def _init_disps():
#	global loadDisp,runDisp,procDisp,blockedDisp,contextDisp,forkDisp,intrDisp
	global workLoadDisp
	global schedDisp
	global timeDisp,cpuDisp,usUtilDisp,arrDisp
	global utilDisp,cpuScattDisp,intrScattDisp
	global memDisp,mstatDisp
	global diskDisp
	global netDisp
	global fileDisp
	global disk_domain,disk_title,disk_width,disk_visible,disk_unit,disk_cut,disk_delimiter,disk_quantity
	global net_domain,net_title,net_width,net_visible,net_unit,net_cut,net_delimiter,net_quantity

	arrDisp		= []
	timeDisp	= Display(["all"],["Hosts_monitors"],[14],[0],[0],[True],["|"],1)
	arrDisp.append(timeDisp)

	workLoadDisp= WorkLoadDisplay(['all','cpu','cpu'],['load','run','proc'],[5,3,4],[0,0,0],[0,1,3],[False,False,False],[" "," "," "],3)
	arrDisp.append(workLoadDisp)
#	loadDisp	= LoadDisplay(["all"],["load"],[5],[0],[0],[False],[" "],1)
#	arrDisp.append(loadDisp)

	cpuDisp		= Display(["cpu"],["cpu"],[3],[2],[0],[False],[" "],1)
	arrDisp.append(cpuDisp)

#	runDisp		= RunDisplay(["cpu"],["run"],[3],[0],[1],[False],[" "],1)
#	arrDisp.append(runDisp)

#	blockedDisp	= BlockedDisplay(["cpu"],["blk"],[3],[0],[1],[False],[" "],1)
#	arrDisp.append(blockedDisp)

#	procDisp	= ProcDisplay(["cpu"],["proc"],[4],[0],[3],[False],[" "],1)
#	arrDisp.append(procDisp)

	utilDisp	= UtilDisplay(['all','all','all','all','all'],["us","sy","io","hi","si"],[2,2,2,2,2],[0,0,0,0,0],[0,0,0,0,0],[False,False,False,False,False],["/","/",'/','/',' '],5)
	arrDisp.append(utilDisp)

	schedDisp	= SchedDisplay(['cpu','cpu','cpu','cpu'],['fork','blk','ctsw','intr'],[4,3,4,4],[0,0,0,0],[3,3,3,3],[False,False,False,False],[" "," "," ","|"],4)
	arrDisp.append(schedDisp)
	
#	contextDisp	= ContextDisplay(["cpu"],["ctsw"],[4],[0],[3],[False],[" "],1)
#	arrDisp.append(contextDisp)

#	intrDisp	= IntrDisplay(["cpu"],["intr"],[4],[0],[3],[False],[" "],1)	
#	arrDisp.append(intrDisp)

#	forkDisp	= ForkDisplay(["cpu"],["fork"],[4],[0],[3],[False],["|"],1)
#	arrDisp.append(forkDisp)

	cpuScattDisp= CpuScattDisplay(['cpu','cpu','cpu'],['Mu','mu','Vu'],[2,2,2],[2,2,2],[0,0,0],[False,False,False],['/','/',' '],3)
	arrDisp.append(cpuScattDisp)
	
	intrScattDisp= IntrScattDisplay(['cpu','cpu','cpu'],['Mirq','mirq','Sirq'],[4,4,4],[2,2,2],[3,3,3],[False,False,False],['/','/','|'],3)	
	arrDisp.append(intrScattDisp)

	fileDisp	= FileDisplay(['fs','fs'],['fopen','fmax'],[5,5],[1,1],[3,3],[False,False],[" ","|"],2)
	arrDisp.append(fileDisp)

	memDisp		= MemDisplay(['mem','mem','mem','mem','mem','mem','mem','mem'],['swap','used','free','ut','buff','cach','pgtb','hgsz'],[4,4,4,2,4,4,4,4],[0,2,0,2,0,0,2,2],[4,4,4,0,4,4,4,4],[False,False,False,False,False,False,False,False],[" "," ",' ',' ',' ',' ',' ','|'],8)
	arrDisp.append(memDisp)

	mstatDisp	= MstatDisplay(['mem','mem','mem','mem'],['pgin','pgou','swpi','swpo'],[4,4,4,4],[2,2,0,0],[3,3,3,3],[False,False,False,False],[' ',' ',' ','|'],4)	
	arrDisp.append(mstatDisp)

	diskDisp	= DiskDisplay(disk_domain,disk_title,disk_width,disk_visible,disk_unit,disk_cut,disk_delimiter,disk_quantity)
	arrDisp.append(diskDisp)

	netDisp		= NetDisplay(net_domain,net_title,net_width,net_visible,net_unit,net_cut,net_delimiter,net_quantity)
	arrDisp.append(netDisp)


def _mon_time():
	global cur_time,timeDisp,cpuDisp

	cur_time = str(time.strftime("%Y/%m/%d %H:%M:%S"))
	timeDisp.setValue2(cur_time)
	cpuDisp.setValue2(cpuCnt)
	timeDisp.calDelta()	
	cpuDisp.calDelta()

def _mon_load():
#	global loadDisp,runDisp,procDisp
	global workLoadDisp
	line	= _readLine("/proc/loadavg")
	workLoadDisp.setValue2(line)
	workLoadDisp.calDelta()

#	loadLine	= _readLine("/proc/loadavg")	
#	loadDisp.setValue2(loadLine)
#	runDisp.setValue2(loadLine)
#	procDisp.setValue2(loadLine)

#	loadDisp.calDelta()
#	runDisp.calDelta()
#	procDisp.calDelta()

def _mon_cpu():
	global	utilDisp,cpuScattDisp
#	global contextDisp,blockedDisp,forkDisp,intrDisp,
	global schedDisp
	
	arrLine		= _readAll("/proc/stat")
	utilDisp.setValue2(arrLine)
	schedDisp.setValue2(arrLine)

#	contextDisp.setValue2(arrLine)
#	blockedDisp.setValue2(arrLine)
#	forkDisp.setValue2(arrLine)
#	intrDisp.setValue2(arrLine)

	cpuScattDisp.setValue2(arrLine)

#	contextDisp.calDelta()
#	blockedDisp.calDelta()
#	forkDisp.calDelta()
#	intrDisp.calDelta()
	schedDisp.calDelta()
	utilDisp.calDelta()
	cpuScattDisp.calDelta()

def _mon_irq():
	global intrScattDisp
	arrLine		= _readAll("/proc/interrupts")
	intrScattDisp.setValue2(arrLine)
	intrScattDisp.calDelta()

def _mon_mem():
	global memDisp
	arrLine		= _readAll("/proc/meminfo")
	memDisp.setValue2(arrLine)
	memDisp.calDelta()

def _mon_mstat():
	global mstatDisp
	arrLine		= _readAll("/proc/vmstat")
	mstatDisp.setValue2(arrLine)	
	mstatDisp.calDelta()

def _mon_disk():
	global diskDisp,arr_device
	arr	= []
	for device in arr_device:
		arr.append(_readLine("/sys/block/"+device +"/stat"))
	diskDisp.setValue2(arr)
	diskDisp.calDelta()

def _mon_net():
	global netDisp
	arrLine		= _readAll("/proc/net/dev")
	netDisp.setValue2(arrLine)
	netDisp.calDelta()

def _mon_file():
	global fileDisp
	arrLine		= _readLine("/proc/sys/fs/file-nr")
	fileDisp.setValue2(arrLine)
	fileDisp.calDelta()
	
def _readLine(filePath):
	try:
		fh   = open(filePath,'r')
		line = fh.readline()
		fh.close()
		return line
	except Exception,e:
		try:
			fh.close()
		except:
			None
		print >>sys.stderr,"Error: "+str(e)
		sys.exit(1)

def _readAll(filePath):
	try:
		fh		= open(filePath,'r')
		arrLine	= fh.readlines()
		fh.close()
		return arrLine
	except Exception,e:
		try:
			fh.close()
		except:
			None
		print >>sys.stderr,"Error: " + str(e)
		sys.exit(1)

def _readRegex():
	None

def clearResource():
	_destory()



class Display:
    def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
        self.domain     = domain
        self.title      = title
        self.width      = width
        #visible 0:core,raw,spec, 1:raw,spec 2:spec 3 core,raw
        self.visible    = visible
        #unit 0:primitve    1:1000 3bytes  2:1024 3bytes,3:10000  4bytes 4:10000 4bytes,k/m/g
        self.unit       = unit
        #cut the value by width
        self.cut        = cut
		#the split charactor
        self.delimiter  = delimiter
		#the array count
        self.quantity	= quantity
		
        self.pre		= None
        self.cur		= None
        self.delta		= None

    def setValue(self,pre,cur,delta):
        self.pre    = pre
        self.cur    = cur
        self.delta  = delta

    def getQuantity(self):
        return self.quantity
 
    def getCur(self):
        return self.cur
    def getUnit(self):
		return self.unit
    def getTitle(self):
        return self.title
    def getDomain(self):
        return self.domain
    def getVisible(self):
        return self.visible
    def getWidth(self):
        return self.width
    def getDelta(self):
        return self.delta
 
	# the default delta calculation
    def calDelta(self):
        self.delta	= [self.cur]
    def getCut(self):
        return self.cut
    def getDelim(self):
        return self.delimiter

    def setValue2(self,cur):
		self.cur	= cur


class WorkLoadDisplay(Display):
	def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
		Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
		self.pre    = None

	def calDelta(self):
		arr	=loadPattern.split(self.cur)
		self.delta	=[arr[0],arr[3],arr[4]]


class LoadDisplay(Display):
    def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
        Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
        self.pre	= None

    def calDelta(self):
        self.delta = [spPattern.split(self.cur)[0]]
		
class RunDisplay(Display):
    def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
        Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
        self.pre	= None

    def calDelta(self):
        self.delta = [spPattern.split(self.cur)[3].split("/")[0]]

class ProcDisplay(Display):
    def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
        Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
        self.pre	= None

    def calDelta(self):
        self.delta = [spPattern.split(self.cur)[3].split("/")[1]]

class UtilDisplay(Display):
	def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
		Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
		self.pre=[0,0,0.0,0,0,0,0,0]

	def calDelta(self):	
		arr_cur	= spPattern.split(self.cur[0].rstrip('\n'))[1:8]
		sumCpu		= 0.0
		for i in range(7):
			sumCpu	= sumCpu + int(arr_cur[i])-int(self.pre[i])
		us	= int((int(arr_cur[0])+int(arr_cur[1])-self.pre[0]-self.pre[1])/sumCpu*100)
		sy	= int((int(arr_cur[2])-self.pre[2])/sumCpu*100)
		io	= int((int(arr_cur[4])-self.pre[4])/sumCpu*100)
		hi	= int((int(arr_cur[5])-self.pre[5])/sumCpu*100)
		si	= int((int(arr_cur[6])-self.pre[6])/sumCpu*100)
		self.pre	= map(int,arr_cur)
		self.delta	= [us,sy,io,hi,si]



class SchedDisplay(Display):
	def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
		Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
		self.pre	=[0,0,0,0]	
		self.delta	=[0,0,0,0]
	def calDelta(self):
		for i in range(len(self.cur)):
			arr = spPattern.split(self.cur[i].rstrip('\n'))
			if arr[0] == 'processes':
				self.delta[0]	= int(arr[1])-self.pre[0]
				self.pre[0]		= int(arr[1])
			elif arr[0] == 'procs_blocked':
				self.delta[1]	= int(arr[1])
			elif arr[0] == 'ctxt':
				self.delta[2]	= int(arr[1])-self.pre[2]
				self.pre[2]		= int(arr[1])
			elif arr[0] == 'intr':
				self.delta[3]	= int(arr[1])-self.pre[3]
				self.pre[3]	= int(arr[1])

					
class ContextDisplay(Display):
	def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
		Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
		self.pre	= 0

	def calDelta(self):
		for i in range(len(self.cur)):
			arr = spPattern.split(self.cur[i].rstrip('\n'))
			if arr[0] == 'ctxt':
				self.delta	= [int(arr[1])-self.pre]
				self.pre	= int(arr[1])
				break

class BlockedDisplay(Display):
    def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
        Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
        self.pre	= None

    def calDelta(self):
        for i in range(len(self.cur)):
            arr	= spPattern.split(self.cur[i].rstrip('\n'))
            if arr[0] == 'procs_blocked':
                self.delta=[arr[1]]
                break

class ForkDisplay(Display):
    def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
        Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
        self.pre	= 0

    def calDelta(self):
        for i in range(len(self.cur)):
            arr = spPattern.split(self.cur[i].rstrip('\n'))
            if arr[0] == 'processes':
                self.delta	= [int(arr[1])-self.pre]
                self.pre	= int(arr[1])
                break

class IntrDisplay(Display):
    def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
        Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
        self.pre	= 0

    def calDelta(self):
        for i in range(len(self.cur)):
            arr = spPattern.split(self.cur[i].rstrip('\n'))
            if arr[0] == 'intr':
                self.delta	= [int(arr[1])-self.pre]
                self.pre	= int(arr[1])
                break

class CpuScattDisplay(Display):
    def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
		Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
		self.pre	=[]
		for i in range(0,cpuCnt+1):
			self.pre.append([0,0,0,0,0,0,0,0,0,0])

    def calDelta(self):
		self.delta	= []
		for i in range(1,cpuCnt+1):
			arr_cur = spPattern.split(self.cur[i].rstrip('\n'))[1:8]
			sumCpu  = 0.0
			for j in range(7):
				sumCpu = sumCpu + int(arr_cur[j])-int(self.pre[i][j])
	
			self.delta.append(int((int(arr_cur[0])+int(arr_cur[1])-self.pre[i][0]-self.pre[i][1])/sumCpu*100))

			for j in range(7):
				self.pre[i][j]  = int(arr_cur[j])	

		self.delta.sort()
		self.delta	=[self.delta[cpuCnt-1],self.delta[0],sum(self.delta)/cpuCnt]

class IntrScattDisplay(Display):
	def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
		Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
		self.pre	=[i-i for i in range(cpuCnt)]

	def calDelta(self):
		self.delta  = []
		cpu_irq_cur	= [i-i for i in range(cpuCnt)]
		for i in range(len(self.cur)):
			arr_cur	= spPattern.split(self.cur[i].strip("\n "))
			if dPattern.match(arr_cur[0]):
				for	j in range(1,cpuCnt+1):
					cpu_irq_cur[j-1]	=cpu_irq_cur[j-1]+int(arr_cur[j])
		for i in range(cpuCnt):
			self.delta.append(cpu_irq_cur[i]-self.pre[i])
			self.pre[i]	=cpu_irq_cur[i]

		self.delta.sort()
		self.delta  =[self.delta[cpuCnt-1],self.delta[0],sum(self.delta)]


					
class MemDisplay(Display):
	def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
		Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
		self.pre	= None
		self.dict	= {}

	def calDelta(self):
		for item in self.cur:
			temp	= spPattern.split(item.rstrip("\n")) 
			self.dict[temp[0]]	=temp[1]

		swap	= (int(self.dict['SwapTotal:']) - int(self.dict['SwapFree:'])) * 1024
		used	= (int(self.dict['MemTotal:']) - int(self.dict['MemFree:'])) * 1024
		free	= int(self.dict['MemFree:']) * 1024
		util	= int(used * 1.0 /(used+free)*100)
		buff	= int(self.dict['Buffers:']) * 1024
		cach	= int(self.dict['Cached:']) * 1024
		pgtb	= int(self.dict['PageTables:']) * 1024
		hgsz	= (int(self.dict['HugePages_Total:']) - int(self.dict['HugePages_Free:'])) * int(self.dict['Hugepagesize:']) * 1024
		self.delta	= [swap,used,free,util,buff,cach,pgtb,hgsz]


class MstatDisplay(Display):
	def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
		Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
		self.pre	= {'pgpgin':0,'pgpgout':0,'pswpin':0,'pswpout':0}
		
	
	def calDelta(self):
		self.dict	={}
		for item in self.cur:
			temp	= spPattern.split(item.rstrip("\n"))
			if temp[0] == 'pgpgin':
				self.dict['pgpgin']		= int(temp[1]) - self.pre['pgpgin']
				self.pre['pgpgin']		= int(temp[1])
			elif temp[0] == 'pgpgout':
				self.dict['pgpgout'] 	= int(temp[1]) - self.pre['pgpgout']
				self.pre['pgpgout']		= int(temp[1])
			elif temp[0] == 'pswpin':
				self.dict['pswpin']		= int(temp[1]) - self.pre['pswpin']
				self.pre['pswpin']		= int(temp[1])
			elif temp[0] =='pswpout':
				self.dict['pswpout'] 	= int(temp[1]) - self.pre['pswpout']
				self.pre['pswpout'] 	= int(temp[1])
		
		self.delta	=[self.dict['pgpgin'],self.dict['pgpgout'],self.dict['pswpin'],self.dict['pswpout']]


class DiskDisplay(Display):
	def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
		Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
		self.pre    =[]
		for i in range(0,len(arr_device)):
			self.pre.append([0,0,0,0,0,0,0,0,0,0,0,0])

	def calDelta(self):
		self.srd  =0
		self.srdz  =0
		self.srdm  =0.0
		self.srdt	=0
		self.swr =0
		self.swrz  =0
		self.swrm  =0.0
		self.swrt	=0

		self.delta	= []

		for i in range(len(self.cur)):
			arr	= spPattern.split(self.cur[i].strip("\n "))
			rd	= int(arr[0]) - self.pre[i][0]
			self.srd	+= rd 
			self.pre[i][0]	= int(arr[0])
			
			rdz	= 512*(int(arr[2]) - self.pre[i][2])
			self.srdz	+= rdz
			self.pre[i][2]	= int(arr[2])

			rdm	= 1.0 * (int(arr[3]) - self.pre[i][3])
			self.srdm	+= rdm
			self.pre[i][3]	= int(arr[3])

			wr    = int(arr[4]) - self.pre[i][4]
			self.swr  += wr
			self.pre[i][4]  = int(arr[4])

			wrz    = 512*(int(arr[6]) - self.pre[i][6])
			self.swrz  += wrz
			self.pre[i][6]  = int(arr[6])

			wrm   = 1.0 * (int(arr[7]) - self.pre[i][7])
			self.swrm  += wrm
			self.pre[i][7]  = int(arr[7])
			
			util  = int(1.0*(int(arr[9])-self.pre[i][9])/(INTERVAL*1000)*100)
			self.pre[i][9]	= int(arr[9])		
			
			queue = (int(arr[10])-self.pre[i][10])/(INTERVAL*1000)
			self.pre[i][10]	= int(arr[10])

			if(rd	==0):
				rdt	=0.0
			else:
				rdt	= float('%.1f'%(rdm/rd))
			if(wr ==0):
				wrt	=0.0
			else:
				wrt	= float('%.1f'% (wrm/wr))
			self.delta.extend([rd,rdz,rdt,wr,wrz,wrt,util,queue])

		if(self.srd ==0):
			self.srdt	=0.0
		else:
			self.srdt	=float('%.1f'%(self.srdm/self.srd))
		if(self.swr	==0):
			self.swrt	=0.0
		else:
			self.swrt	=float('%.1f'%(self.swrm/self.swr))
		
		self.delta.extend([self.srd,self.srdz,self.srdt,self.swr,self.swrz,self.swrt])

class NetDisplay(Display):
	def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
		Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
		self.pre    =[]
		for i in range(0,len(arr_eth)+1):
			self.pre.append([0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0])
		self.dict   = {}

	def calDelta(self):
		self.delta	= []
		loop	= -1
		for i in range(len(self.cur)):
			arr	= netPattern.split(self.cur[i].strip("\n "))
			if arr[0] in arr_eth or arr[0] == bond:
				loop += 1

				Rvz					=	int(arr[1]) - self.pre[loop][1]
				self.pre[loop][1]	=	int(arr[1])
				Rv					= 	int(arr[2]) - self.pre[loop][2]
				self.pre[loop][2]	=	int(arr[2])
				Rve					=	int(arr[3])+int(arr[4]) - self.pre[loop][3]- self.pre[loop][4]
				self.pre[loop][3]	=	int(arr[3])
				self.pre[loop][4]	=   int(arr[4])
				
				Tmz                 =   int(arr[9]) - self.pre[loop][9]
				self.pre[loop][9]   =   int(arr[9])
				Tm                 =   int(arr[10]) - self.pre[loop][10]
				self.pre[loop][10]  =   int(arr[10])
				Tme                 =   int(arr[11])+int(arr[12]) - self.pre[loop][11] - self.pre[loop][12]
				self.pre[loop][11]  =   int(arr[11])
				self.pre[loop][12]  =   int(arr[12])
				self.dict[arr[0]]   = [Rv,Rvz,Rve,Tm,Tmz,Tme]
		for item in arr_eth:
				self.delta.extend(self.dict[item])
		self.delta.extend(self.dict[bond])

class FileDisplay(Display):
	def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
		Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
	
	def calDelta(self):
		self.delta	= []
		arr			= spPattern.split(self.cur.strip("\n"))
		self.delta	= [arr[0],arr[2]]

if __name__ == '__main__':
	try:
		try:
			chkEnv()
			initEnv()
			while(1):
#				start	=datetime.now()
				loopMon()
				if LOOP%10 ==0:
					loopTitle()
				if LOOP%100 ==0:
					copyFile()
				if(LOOP != 0):
					loopDisp()
#				end		=datetime.now()
#				print end - start
				time.sleep(INTERVAL)
				if(LOOP>500000 and cur_time[11:16]=='04:59'):
					exit(0)
				LOOP += 1
		except Exception,e:
			print >>sys.stderr,"Error: " +str(e)
	finally:
			clearResource()
			sys.exit(1)