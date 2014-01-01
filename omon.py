#!/usr/bin/python
#Requirment:
#	python version > 2.2
#	kernel > 2.6.18
#	Directory:/home/oracle/	
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
import subprocess
from datetime import datetime

VERSION 	= '0.1'
DIRMON		= '/home/oracle/admin/'
INTERVAL	= 2
LOOP		= 0
ORACLE_CORE	= 'oracle_core.log'
ORACLE_PLUS	= 'oracle_plus.log'
ORACLE_RAW	= 'oracle_raw.log'
ORACLE_FLK	= '.oracle_lock.flk'
MAXSIZE		= 52428800
SID			= None
ORACLE_HOME	= None

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

def _initOracleEnv():
	global ORACLE_CORE,ORACLE_PLUS,ORACLE_RAW,ORACLE_FLK
	ORACLE_CORE 	= ORACLE_CORE + '_' + SID
	ORACLE_PLUS		= ORACLE_PLUS + '_' + SID
	ORACLE_RAW 		= ORACLE_RAW + '_' + SID
	ORACLE_FLK 		= ORACLE_FLK + '_' + SID

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
		fd_flk	= os.open(DIRMON+ORACLE_FLK,os.O_CREAT|os.O_WRONLY)
		fcntl.lockf(fd_flk,fcntl.LOCK_EX|fcntl.LOCK_NB)
	except IOError,e:
		print >>sys.stderr,"warn: " +str(e)
		try:
			fcntl.lockf(fd_flk,fcntl.LOCK_UN)
			os.close(fd_flk)
		except Exception,e:
			print >>sys.stderr,"Warn: " +str(e)
		sys.exit(1)

#init the log file description,and set buffersize
def _init_fd():
	global fh_core,fh_plus,fh_raw
	global fh_arr,fl_arr
	try:
		fh_core	= os.fdopen(os.open(DIRMON+ORACLE_CORE,os.O_RDWR|os.O_APPEND|os.O_CREAT),'a+',512)
		fh_plus	= os.fdopen(os.open(DIRMON+ORACLE_PLUS,os.O_RDWR|os.O_APPEND|os.O_CREAT),'a+',512)
		fh_raw	= os.fdopen(os.open(DIRMON+ORACLE_RAW,os.O_RDWR|os.O_APPEND|os.O_CREAT),'a+',512)
		fh_arr	= [fh_core,fh_plus,fh_raw]
		fl_arr	= [DIRMON+ORACLE_CORE,DIRMON+ORACLE_PLUS,DIRMON+ORACLE_RAW]
	except Exception,e:
		print >>sys.stderr,"Error: " +str(e)
		sys.exit(1)


def copyFile():
	try:
		statinfo	= os.stat(DIRMON+ORACLE_CORE)
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
	global spPattern,dPattern,netPattern,loadPattern
	spPattern	=re.compile("\s+")
	dPattern	=re.compile("\d+:")
	netPattern	=re.compile("\s+|:[\s\t]*|\t+")
	loadPattern	=re.compile("\s+|/")			

def _init_oraEnv():
	global ORACLE_HOME,SQLPLUS
	ORACLE_HOME	= os.environ.get("ORACLE_HOME")
	SQLPLUS		= ORACLE_HOME+"/bin/sqlplus"
	if not os.path.exists(SQLPLUS):
		print >>sys.stderr,"Error:not exists sqlplus!"
		sys.exit(1)
	SQLPLUS 	= SQLPLUS + " -s / as sysdba "

def initEnv():
	#int the monitor directry  
	_init_path(DIRMON)
	#append the sid to the filename
	_initOracleEnv()
	#get excusive lock
	_init_flock()
	#init the log file description
	_init_fd()
	#init global variables
	_init_globalVar()
	
	_init_oraEnv()	
	#init display class for cpu,mem,net,disk,fs and so on	
	_init_disps()

def loopMon():
	_mon_time()
	_mon_load()
	_mon_cpu()
	_mon_orastat()

def loopDisp():
	global rawValue,dispValue
	for disp in arrDisp:
		for i in range(disp.getQuantity()):
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
				fh_plus.write(formatWidth(width) % (dispValue))
				fh_plus.write(delim)
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
				fh_plus.write(formatWidth(disp.getWidth()[i]) % (title))
				fh_plus.write(disp.getDelim()[i])

	endLine()

def endLine():
	fh_core.write("\n")
	fh_raw.write("\n")
	fh_plus.write("\n")
	fh_core.flush()
	fh_raw.flush()
	fh_plus.flush()

def _init_disps():
	global arrDisp
	global workLoadDisp,timeDisp,utilDisp,orastatDisp
	
	arrDisp		= []
	timeDisp	= Display(["all"],["Oracle_monitor"],[14],[0],[0],[True],["|"],1)
	arrDisp.append(timeDisp)

	workLoadDisp= WorkLoadDisplay(['all','all','all'],['load','run','proc'],[5,3,4],[3,-1,-1],[0,1,3],[False,False,False],[" "," "," "],3)
	arrDisp.append(workLoadDisp)

	utilDisp	= UtilDisplay(['all','all','all','all','all'],["us","sy","io","hi","si"],[2,2,2,2,2],[3,3,3,3,3],[0,0,0,0,0],[False,False,False,False,False],["/","/",'/','/','|'],5)
	arrDisp.append(utilDisp)

	ora_domain	=['all','all','all','all','all','all','all','all','all','all','all','all','all','all','all','all','all','all','all','all','all','all']
	ora_title	=['Act','Enq','Log','Sess','Logf','Pars','Exec','Comm','Roll','Clean','Redo','Rwrt','Rsyn','Rrst','Bget','Cget','Sort','Read','Writ','Trip','Send','Recv']
	ora_width 	=[3,3,3,5,4,4,4,4,4,5,4,4,4,5,4,4,4,4,4,4,4,4]
	ora_visible =[3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3]
	ora_unit 	=[0,0,0,0,0,3,3,3,3,3,4,3,3,0,3,3,3,3,3,3,4,4]
	ora_cut 	=[False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False]
	ora_delim 	=[" "," "," ","|"," "," "," "," "," ","|"," "," "," ","|"," "," "," "," ","|"," "," ","|"]

	orastatDisp	= OrastatDisplay(ora_domain,ora_title,ora_width,ora_visible,ora_unit,ora_cut,ora_delim,22)
	arrDisp.append(orastatDisp)

def _mon_time():
	global cur_time,timeDisp
	cur_time = str(time.strftime("%Y/%m/%d %H:%M:%S"))
	timeDisp.setValue2(cur_time)
	timeDisp.calDelta()	

def _mon_load():
	global workLoadDisp
	line	= _readLine("/proc/loadavg")
	workLoadDisp.setValue2(line)
	workLoadDisp.calDelta()

def _mon_cpu():
	global	utilDisp
	arrLine		= _readAll("/proc/stat")
	utilDisp.setValue2(arrLine)
	utilDisp.calDelta()

def _mon_orastat():
	global  orastatDisp
	sql_active	="select 'Active',count(*) from v$session where status='ACTIVE' and type='USER'"
	sql_session ="select 'Session',count(*) from v$session"
	sql_enqueue ="select 'Enqueue',count(*) from v$session_wait where event like 'enq:%'"
	sql_logfile	="select 'logf',count(*) from v$log where ARCHIVED='YES' and STATUS='INACTIVE'"
	sql_stat	="select decode(name,'logons cumulative','Log', 'user commits','Comm', 'execute count','Exec','user rollbacks','Roll', 'cleanouts and rollbacks - consistent read gets','Clean', 'redo size','Redo', 'redo writes','Rwrt', 'redo synch writes','Rsyn', 'redo synch time','Rrst', 'sorts (rows)','Sort', 'parse count (hard)','Parse', 'db block gets','Bget', 'consistent gets','Cget', 'physical read IO requests','Read', 'physical write IO requests','Writ', 'bytes sent via SQL*Net to client','Send', 'bytes received via SQL*Net from client','Recv', 'SQL*Net roundtrips to/from client','Trip'),value from v$sysstat where  name in('logons cumulative', 'user commits', 'user rollbacks', 'cleanouts and rollbacks - consistent read gets', 'redo size', 'redo writes', 'redo synch writes', 'redo synch time', 'sorts (rows)', 'parse count (hard)', 'db block gets', 'consistent gets', 'physical read IO requests', 'physical write IO requests', 'bytes sent via SQL*Net to client', 'bytes received via SQL*Net from client', 'SQL*Net roundtrips to/from client','execute count') "


	sqlArray 	=[sql_active,sql_session,sql_enqueue,sql_logfile,sql_stat]

	arrLine		= _oraClient(sqlArray)
	orastatDisp.setValue2(arrLine)
	orastatDisp.calDelta()

def _oraClient(sqlArray):
	global ORACLE_HOME,SQLPLUS
	try:
		proc    = subprocess.Popen(SQLPLUS,shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		proc.stdin.write("set feedback off echo off heading off numwidth 50\n")
		for sql in sqlArray:
			proc.stdin.write(sql+";\n")
		proc.stdin.write("exit;\n")
		result 	= proc.stdout.readlines()
		retcode	= proc.wait()
		if retcode == 0:
			return result
		return None	
	except Exception,e:
		return None

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
			return None
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
			return None
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
		#visible 0:core,raw,plus, 1:raw,plus 2:plus 3 core,raw
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

class OrastatDisplay(Display):
	def __init__(self,domain,title,width,visible,unit,cut,delimiter,quantity):
		Display.__init__(self,domain,title,width,visible,unit,cut,delimiter,quantity)
		self.pre=[0,0,0.0,0,0,0,0,0,0,0,0,0.0,0,0,0,0,0,0]
	def calDelta(self):
		self.delta 	= []
		statLines	= self.cur
		for line in statLines:
			line    =line.rstrip(" \n")
			if line =="":
				continue
			[key,value] = spPattern.split(line)
			if key =="Active":
				active 	= int(value)
			elif key =="Session":
				session = int(value)
			elif key =="Enqueue":
				enqueue = int(value)
			elif key =="Log":
				log 	= int(value) -self.pre[0]
				self.pre[0] 	=int(value)
			elif key =="Exec":
				exect 	= int(value) -self.pre[1]
				self.pre[1] 	=int(value)
			elif key =="Comm":
				comm 	= int(value) -self.pre[2]
				self.pre[2] 	=int(value)				
			elif key =="Roll":
				roll 	= int(value) -self.pre[3]
				self.pre[3] 	=int(value)	
			elif key =="Clean":
				clean 	= int(value) -self.pre[4]
				self.pre[4] 	=int(value)	
			elif key =="Redo":
				redo 	= int(value) -self.pre[5]
				self.pre[5] 	=int(value)	
			elif key =="Rwrt":
				rwrt 	= int(value) -self.pre[6]
				self.pre[6] 	=int(value)	
			elif key =="Rsyn":
				rsyn 	= int(value) -self.pre[7]
				self.pre[7] 	=int(value)	
			elif key =="Rrst":
				rrst 	= int(value) -self.pre[8]
				self.pre[8] 	=int(value)	
			elif key =="Bget":
				Bget 	= int(value) -self.pre[9]
				self.pre[9] 	=int(value)
			elif key =="Cget":
				Cget 	= int(value) -self.pre[10]
				self.pre[10] 	=int(value)
			elif key =="Parse":
				Parse 	= int(value) -self.pre[11]
				self.pre[11] 	=int(value)				
			elif key =="Sort":
				Sort 	= int(value) -self.pre[12]
				self.pre[12] 	=int(value)	
			elif key =="Read":
				Read 	= int(value) -self.pre[13]
				self.pre[13] 	=int(value)	
			elif key =="Writ":
				Writ 	= int(value) -self.pre[14]
				self.pre[14] 	=int(value)	
			elif key =="Send":
				Send 	= int(value) -self.pre[15]
				self.pre[15] 	=int(value)	
			elif key =="Recv":
				Recv 	= int(value) -self.pre[16]
				self.pre[16] 	=int(value)	
			elif key =="Trip":
				Trip 	= int(value) -self.pre[17]
				self.pre[17] 	=int(value)	
			elif key =="logf":
				logf 	= int(value)
		if(rsyn ==0):
			rrst ="0.00"
		else:				
			rrst = ("%.2f"%(rrst*10/(rsyn*1.0)))
		self.delta 	=[active,enqueue,log,session,logf,Parse,exect,comm,roll,clean,redo,rwrt,rsyn,rrst,Bget,Cget,Sort,Read,Writ,Trip,Send,Recv]



if __name__ == '__main__':
#	try:
#		try:
			if len(sys.argv)>1:
				SID	=str(sys.argv[1])
			else:
				print >>sys.stderr,"Error: pls input oracle SID!"
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
#		except Exception,e:
#			print >>sys.stderr,"Error: " +str(e)
#	finally:
#			clearResource()
#			sys.exit(1)