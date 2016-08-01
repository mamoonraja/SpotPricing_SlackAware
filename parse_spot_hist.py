#! /usr/bin/python
import json
import time
import datetime
import pickle
import sys
import numpy as np
from myPlot import myplot
import random

'''
	To run simple parser:
		python parse_spot_hist.py 1 Instance.Type

	To analyze run:
		python parse_spot_hist.py 2 InstanceType analysis_type
'''

class Parser(object): # simply parse thejson files and store required information as a dictionay in .p files
	def __init__(self,typ):
		self.zonelist='us-east-1 eu-west-1 ap-northeast-1'.split()
		self.itypes='m4.large m4.xlarge m4.2xlarge m4.4xlarge'.split()
		self.ityp=typ
		self.prices={}
		self.nodes_prices={}
		self.start_time=int(time.mktime(time.strptime('2016/03/22 00:08:09', "%Y/%m/%d %H:%M:%S")))
		self.nas=0

	def parse_indiv(self,zlist): # parse every zone individually
		for zone in zlist:
			self.prices[zone]={}
			data = json.load(open('./'+self.ityp+'/'+zone+'.json'))
			for elem in data['SpotPriceHistory']:
				t=self.conv_time(elem['Timestamp'])
				try:
					self.prices[zone][t]
				except:
					self.prices[zone][t]=elem['SpotPrice']
				else:
					if float(elem['SpotPrice']) < float(self.prices[zone][t]):
						self.prices[zone][t]=elem['SpotPrice']

	def parse_pairs(self,src,dest,relay): # parse for paths, i.e in pairs
		for key,val in self.prices[src].iteritems():
			src_rate=val
			try:
				dest_rate=self.prices[dest][key]
			except:
				dest_rate=self.find_prev_time(dest,key)
			try:
				relay_rate=self.prices[relay][key]
			except:
				relay_rate=self.find_prev_time(relay,key)
			self.nodes_prices[key]=src_rate+' '+dest_rate+' '+relay_rate

	def conv_time(self,t):
		return int(time.mktime(time.strptime(t.replace("-","/").replace("Z","").replace("T"," ").split(".")[0], "%Y/%m/%d %H:%M:%S")))

	def find_prev_time(self,zone,current_ts): # go bcakward from currect time to find price in past
		i=current_ts
		for i in range(current_ts,current_ts-108000,-1):
			try:
				self.prices[zone][i]
			except:
				pass
			else:
				return self.prices[zone][i]
		self.nas+=1
		print "NA"
		return "NA"

	def dump_to_dict(self):
		pickle.dump(self.nodes_prices,open('node_prices_'+self.ityp.split('.')[0]+self.ityp.split('.')[1]+'.p','wb'))
		pickle.dump(self.prices,open('all_prices_'+self.ityp.split('.')[0]+self.ityp.split('.')[1]+'.p','wb'))


class Analysis(object): # load the dict from pickle dump and we do the analysis here
	def __init__(self,dict_file):
		self.dic=pickle.load( open( dict_file, "rb" ) )

	def cheapest_by_time(slef,Keys,dic): # find cheapest price in slot
		mins=[]
		ts=[]
		for key in Keys:
			v=dic[key].split()
			ts.append(int(key))
			mins.append(v.index(min(v)))
			print key,dic[key],v.index(min(v))
		return [ts,mins]

	def prices_by_hour(self,ks,dc): # get hourly prices
		s={}
		d={}
		r={}
		for k in ks:
			t=int(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(k)).split()[1].split(':')[0])
			h=int(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(k)).split()[1].split(':')[0])
			m=int(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(k)).split()[1].split(':')[1])
			try:
				s[t]
			except:
				s[t]=[float(dc[k].split()[0])]
				d[t]=[float(dc[k].split()[1])]
				r[t]=[float(dc[k].split()[2])]
			else:
				s[t].append(float(dc[k].split()[0]))
				d[t].append(float(dc[k].split()[1]))
				r[t].append(float(dc[k].split()[2]))
		return [s,d,r]

	def plot_hourly_agg(self,s,d,r):
		ts=s.keys()
		sMeans=[]
		dMeans=[]
		rMeans=[]
		print len(s)
		for k in ts:
			sMeans.append(np.percentile(np.array(s[k]),95))
			dMeans.append(np.percentile(np.array(d[k]),95))
			rMeans.append(np.percentile(np.array(r[k]),95))
		mp=myplot()
		xx=range(0,24)
		s1=[item for sublist in s for item in s[sublist]]
		d1=[item for sublist in d for item in d[sublist]]
		r1=[item for sublist in r for item in r[sublist]]
		xx2=range(0,len(s1))
		print len(s1),len(xx2)
		sorted_indices=[i[0] for i in sorted(enumerate(s1), key=lambda x:x[1])]
		s2=[]
		d2=[]
		diff=[]
		for j in sorted_indices:
			s2.append(s1[j])
			diff.append((abs(s1[j]-d1[j])/s1[j])*100)
			d2.append(d1[j])
		mp.plot_simple([sMeans,dMeans,rMeans],xx,['Source (US)','Dest (AS)','Relay (EU)'],'time','price',4)

	def prices_in_slack(self,key,d,s):
		ts=[]
		srs=[]
		ds=[]
		rs=[]
		for k in range(key,key+s*2):
			try:
				d[k]
			except:
				pass
			else:
				al=d[k].split()
				ts.append(k)
				srs.append(float(al[0]))
				ds.append(float(al[1]))
				rs.append(float(al[2]))
		return [ts,srs,ds,rs]


	def iter_after_slack(self,Keys,dic,slack,trtime,bid_factor,iter_factor):
		k=0
		prev=Keys[0]
		c_s=[]
		i_s=[]
		for i in Keys:
			if i-prev>iter_factor: # starting from 2nd slot, so that we have past data
				[cost,intrpt]=self.check_slack_strategic(i,dic,slack,prev,trtime,bid_factor,1)
				c_s.append(cost)
				i_s.append(intrpt)
				prev=i
				k+=1
		return [c_s,i_s]


	def get_costs(self,sorted_one,tstamps,src_cost,dest_cost,total_cost,trtime):
		total_t=0
		s_p=0
		d_p=0
		t_p=0
		for i in sorted_one:
			try:
				tstamps[i+1]
			except:
				pass
			else:
				if total_t >trtime:
					return total_t,s_p/total_t,d_p/total_t,t_p/total_t
				t_dur=tstamps[i+1]-tstamps[i]
				s_p+=t_dur*src_cost[i]
				d_p+=t_dur*dest_cost[i]
				t_p+=t_dur*total_cost[i]
				total_t+=t_dur
		return total_t,s_p/total_t,d_p/total_t,t_p/total_t


	def calc_slack_price(self,tstamps,src_cost,dest_cost,total_cost,slack,trtime,strategy):
		'''calculating prices for specific slacks here
		'''
		if slack==trtime: 
			s_p=0
			total_t=0
			d_p=0
			t_p=0
			for i in range(len(tstamps)-1):
				t_dur=tstamps[i+1]-tstamps[i]
				s_p+=t_dur*src_cost[i]
				d_p+=t_dur*dest_cost[i]
				t_p+=t_dur*total_cost[i]
				total_t+=t_dur
			return total_t,s_p/total_t,d_p/total_t,t_p/total_t
		else:
			if strategy==1:
				sorted_one=[i[0] for i in sorted(enumerate(src_cost), key=lambda x:x[1])]
			elif strategy==2:
				sorted_one=[i[0] for i in sorted(enumerate(dest_cost), key=lambda x:x[1])]
			elif strategy==3:
				sorted_one=[i[0] for i in sorted(enumerate(total_cost), key=lambda x:x[1])]
			[total_t,s_p,d_p,t_p]=self.get_costs(sorted_one,tstamps,src_cost,dest_cost,total_cost,trtime)
			return total_t,s_p,d_p,t_p



	def check_slack_simple(self,Keys,dic,slack,trtime,ti,strategy): #ti, is start time for this iter
		all_prices=self.prices_in_slack(ti,dic,slack) # current slack
		index=0
		start_time = all_prices[0][index]
		timer=start_time
		ts=[]
		src_c=[]
		dest_c=[]
		total=[]
		while timer - start_time < slack:
			ts.append(all_prices[0][index])
			src_c.append(all_prices[1][index])
			dest_c.append(all_prices[2][index])
			total.append(all_prices[1][index]+all_prices[2][index])
			index+=1
			print index
			timer=all_prices[0][index]
		ts.append(all_prices[0][index])
		src_c.append(all_prices[1][index])
		dest_c.append(all_prices[2][index])
		total.append(all_prices[1][index]+all_prices[2][index])
		[ts,sc,dc,tot_c]=self.calc_slack_price(ts,src_c,dest_c,total,slack,trtime,strategy)
		return [ts,sc,dc,tot_c]


	def check_slack_iter_start_time(self,Keys,dic,slack,trtime,request_times,strategy):
		ts=[]
		ss=[]
		ds=[]
		total_price=[]
		imp=[]
		k=0
		prev=request_times[0]
		last=request_times[-1]
		for i in request_times:
			[tn,sn,dn,totcn]=self.check_slack_simple(Keys,dic,trtime,trtime,i,strategy)
			[t,s,d,totc]=self.check_slack_simple(Keys,dic,slack,trtime,i,strategy)
			prev=i
			k+=1
			ts.append(t)
			ss.append(s)
			ds.append(d)
			total_price.append(totc)
			p_var=float(totcn-totc)/float(totcn)
			imp.append(p_var*100)
		return imp

	def select_req_times(self,Ks,maxslack): # select unique times
		times=[]
		count=0
		prev=Ks[0]
		for k in Ks:
			if k - prev > random.randint(60,360):
				times.append(k)
				count+=1
				prev=k
			if count>=10000:
				break
		return times


	def vary_slack_time(self,Keys,dic,slack,trtime):
		ts=[[],[],[]]
		stds=[[],[],[]]
		slacks=range(slack,21*3600,3600)
		smins=[]
		iter_factor=self.select_req_times(Keys)
		print len(iter_factor)
		print iter_factor
		for s in slacks:
			costs=self.check_slack_iter_start_time(Keys,dic,s,trtime,iter_factor,1)
			costs2=self.check_slack_iter_start_time(Keys,dic,s,trtime,iter_factor,2)
			costs3=self.check_slack_iter_start_time(Keys,dic,s,trtime,iter_factor,3)
			ts[0].append(np.percentile(costs,95))
			ts[1].append(np.percentile(costs2,95))
			ts[2].append(np.percentile(costs3,95))
			stds[0].append(np.std(costs))
			stds[1].append(np.std(costs2))
			stds[2].append(np.std(costs3))
			smins.append(float(s)/float(3600))
		mp=myplot()
		sss=map(str,smins)
		mp.plot_simple(ts,smins,['source','destination','optimized'],'slack ','prices',1)

	def vary_trtime(self,Keys,dic,slack,trtime):
		p99=[[],[],[]]
		means=[[],[],[]]
		stds=[[],[],[]]
		times=[600,1800,3600]
		smins=[]
		iter_factor=self.select_req_times(Keys,20*3600)
		print len(iter_factor)
		windows=[3600*2,5*3600,10*3600,20*3600] #windows for slack
		for w in windows:
			i=0
			print "w,",w
			for tr in times:
				costs=self.check_slack_iter_start_time(Keys,dic,w,tr,iter_factor,3)
				print len(costs)
				p99[i].append(np.percentile(costs,95))
				means[i].append(np.mean(costs))
				stds[i].append(np.std(costs))
				i+=1
		print "windows=",windows
		print "means=",means
		print "stds=",stds
		print "perc95=",p99
		mp=myplot()
		mp.get_hist(len(windows),means[0],stds[0],means[1],stds[1],means[2],stds[2],windows,('Transfer time = 10 minutes','Trensfer time = 30 minutes','Trensfer time = 60 minutes'))
#		mp.plot_simple(ts,smins,['slack=5 hours','slack = 10hours','slack = 20hours'],'Transfer time','prices',2)



	def vary_perc_changes(self,Keys,dic,perc_change):
		start=Keys[0]
		step_size=[]
		price_var=[]
		small_change_p_var=[]
		small_step=[]
		rest_p_var=[]
		for k in Keys[1:-1]:
			p_var=(abs(float(dic[k].split()[0]) - float(dic[start].split()[0]))\
			      /float(float(dic[start].split()[0])))*100
			if p_var>perc_change:
				step_size.append(k-start)
				if k - start < 60:
					small_change_p_var.append(p_var)
					small_step.append(k-start)
				else:
					rest_p_var.append(p_var)
				price_var.append(p_var)
			start=k
		print "perc ", perc_change
		print "raw analysis: step ",len(step_size),max(step_size),min(step_size),np.percentile(step_size,50)
		#print "raw analysis: prices ",len(price_var),max(price_var),min(price_var),np.percentile(price_var,50)
		#print "raw analysis: small prices ",len(small_change_p_var),max(small_change_p_var),min(small_change_p_var),np.percentile(small_change_p_var,50)
		print " times where step size is less than 60s",float(len(small_change_p_var))/float(len(price_var))
		return step_size,small_change_p_var,rest_p_var,price_var

	def cost_with_relay(self,dic,t,w,oldp):
		relay_prices=[]
		for i in range(t,t+w):
			try:
				dic[i]
			except:
				pass
			else:
				s_r=float(dic[i].split()[0])+float(dic[i].split()[2])
				for j in range(t+1,t+w):
					try:
						dic[j]
					except:
						pass
					else:
						r_d=float(dic[j].split()[2])+float(dic[j].split()[1])
						relay_prices.append(s_r+r_d)
		if len(relay_prices)==0:
		# or min(relay_prices)>oldp:
			return oldp
		else:
			return min(relay_prices)

	def rate_in_window(self,dic,t,w,strat):
		rs=[]
		frst=float(dic[t].split()[0])
		minv=frst
		for elem in range(t,t+w):
			try:
				dic[elem]
			except:
				pass
			else:
				if float(dic[elem].split()[0]) < minv:
					minv=float(dic[elem].split()[0])
 		return frst,minv

 	def fullcost_in_window(self,dic,t,w,strat):
		frst_src=float(dic[t].split()[0]) #first_main is the one to consider before deciding
		frst_dst=float(dic[t].split()[1])
		min_src=frst_src
		min_dst=frst_dst
		for elem in range(t,t+w):
			try:
				dic[elem]
			except:
				pass
			else:
				if strat==1:
					if float(dic[elem].split()[0]) < min_src:
						min_src=float(dic[elem].split()[0])
						min_dst=float(dic[elem].split()[1])
				if strat==2:
					if float(dic[elem].split()[1]) < min_dst:
						min_src=float(dic[elem].split()[0])
						min_dst=float(dic[elem].split()[1])
				if strat==3:
					if float(dic[elem].split()[1])+float(dic[elem].split()[0])\
					 < min_dst+min_src:
						min_src=float(dic[elem].split()[0])
						min_dst=float(dic[elem].split()[1])
				if strat==4:
					total_cost=self.cost_with_relay(dic,t,w,frst_src+frst_dst)
					return frst_src+frst_dst,total_cost
		return frst_src+frst_dst,min_src+min_dst


	def find_cost_reductions(self,Keys,dic,window,strategy,typ):
		diffs=[]
		pr=Keys[0]
		iter_step=random.randint(60,600)
		for it in range(3):
			ks=list(Keys)
			pr=ks[0]
			for i in range(len(ks)):
				t=ks[i]
				if t-pr>iter_step:
					if typ==3:
						[rate_start,rate_min]=self.fullcost_in_window(dic,t,window,strategy)
					elif typ==2:
						[rate_start,rate_min]=self.rate_in_window(dic,t,window,strategy)
					p_var=(float(rate_start - rate_min)) / float(rate_start) *100
					diffs.append(p_var)
					pr=t
					iter_step=random.randint(60,600)
		print window,float(len(diffs)),np.percentile(diffs,50)
		return diffs

	def only_prices(self,Keys,dic):
		ps=[]
		ts=[]
		k0=Keys[0]
		for k in Keys:
			ps.append(float(dic[k].split()[0]))
			ts.append(float(k-k0)/float(3600))
		return [ts,ps]

	def price_stats_indiv(self,Keys,dic):
		[all_t,all_prices]=self.only_prices(Keys,dic)
		np.percentile(all_prices,50),np.percentile(all_prices,95),np.percentile(all_prices,99)

	def check_time_vars_raw_data(self,Keys,dic,all_ps,typ):
		mp=myplot()
		Keys1 = sorted(all_ps['eu-west-1'].keys())
		Keys2 = sorted(all_ps['ap-northeast-1'].keys())
		if typ==1:
			perc_changes=range(0,1,10)
			sss=[]
			for change in perc_changes:
				[step_size,small_change,rest_p_var,all_var]=self.vary_perc_changes(Keys,dic,change)
				sss.append(step_size)
			mp.plot_cdf(sss,perc_changes,'step','CDF',4,False)
			mp.plot_cdf([rest_p_var,small_change,all_var],\
				['price variations for chages of larger durations','price variations for shorter duration changes','all']\
				,'price change (%)','CDF',4,False)

		elif typ==2: # for one side costs
			outfile=open('stats_costs_regions_AS.p','wb')
			diffs=[[],[],[]]
			perc95=[[],[],[]]
			perc25=[[],[],[]]
			means=[[],[],[]]
			meds=[[],[],[]]
			stds=[[],[],[]]
			all_dic=[dic,all_ps['eu-west-1'],all_ps['ap-northeast-1']]
			all_keys=[Keys,Keys1,Keys2]
			windows=[600,1800,3600,5*3600,10*3600,20*3600] #windows for slack
			for window in windows:
				for strat in range(1,3):
					out=self.find_cost_reductions(all_keys[strat],all_dic[strat],window,1,typ)
					diffs[strat].append(out)
					means[strat].append(np.mean(out))
					meds[strat].append(np.percentile(out,50))
					stds[strat].append(np.std(np.array(out)))
					perc95[strat].append(np.percentile(out,95))
					perc25[strat].append(np.percentile(out,25))
			pickle.dump(diffs,outfile)
			mp.get_hist(len(windows),means[0],stds[0],means[1],stds[1],means[2],stds[2],windows,('US','EU','AS'))
			mp.plot_cdf(diffs[2],['Slack = 5 Minutes','Slack = 30 Minutes','Slack = 1 Hour','Slack = 5 Hours'],'Price Reduction (%)','CDF',4,False)

		elif typ==3: #full path cost for diff windows
			outfile=open('stats_fullcost_strategies.p','wb')		
			diffs=[[],[],[]]
			windows=[300,600,1800,3600,5*3600,10*3600,20*3600] #windows for slack
			means=[[],[],[]]
			stds=[[],[],[]]
			perc95=[[],[],[]]
			perc25=[[],[],[]]
			for window in windows:
				for s in range(1,4):
					c=self.find_cost_reductions(Keys,dic,window,s,typ)
					diffs[s-1].append(c)
					means[s-1].append(np.mean(c))
					stds[s-1].append(np.std(c))
					perc95[s-1].append(np.percentile(c,95))
					perc25[s-1].append(np.percentile(c,25))
			pickle.dump(diffs,outfile)			
			mp.get_hist(len(windows),means[0],stds[0],means[1],stds[1],means[2],stds[2],windows,('Source','Dest','Joint Optimized'))

		elif typ==4: #full path cost for specific windows and cdf
			imps=[]
			strategy=range(1,5)
			for s in strategy:
				c=self.find_cost_reductions(Keys,dic,10800,s,3)
				imps.append(c)
			mp.plot_cdf(imps,['s','d','o','r'],'Price Reduction (%)','CDF',4,False)
		elif typ==5:
			self.price_stats_indiv(sorted(Keys1),all_ps['eu-west-1'])
			self.price_stats_indiv(sorted(Keys2),all_ps['ap-northeast-1'])
			self.price_stats_indiv(sorted(Keys),dic)


	def analyze_data(self,Keys,dic,all_prices,slack,trtime,typ):
		#[hs,hd,hr]=self.prices_by_hour(Keys,dic)
		#self.plot_hourly_agg(hs,hd,hr)
		self.check_time_vars_raw_data(Keys,dic,all_prices,typ) # for analysis on simple one side price
		#and for very smal transfer(for total costs) times (actually agnostic of transfer times)
		#self.vary_trtime(Keys,dic,3600,300)

if int(sys.argv[1])==1: #parse
	p=Parser(sys.argv[2])
	p.parse_indiv(p.zonelist)
	p.parse_pairs('us-east-1','ap-northeast-1','eu-west-1') # src, dest, relay
	p.dump_to_dict()

elif int(sys.argv[1])==2: #analyze
	an=Analysis('node_prices_'+sys.argv[2]+'.p')
	all_p=Analysis('all_prices_'+sys.argv[2]+'.p') # to see original prices of all
	#instead of times where changes are w.r.t source
	an.analyze_data(sorted(an.dic.keys()),an.dic,all_p.dic,600,600,int(sys.argv[3]))
