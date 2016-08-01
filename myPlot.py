import matplotlib.pyplot as plt
from pylab import *
import numpy as np

# Some custom written routines to plot for certain scenarios
# TODO: lacks modularity and needs to be documented, 

class myplot(object):
	def plot_simple(self,datas,datax,labels,xl,yl,location):
		fsize=18
		ax = figure().add_subplot(111)
		for label in (ax.get_xticklabels() + ax.get_yticklabels()):
		    label.set_fontsize(fsize)				
		linestyles = ['-', ':', '--', '-.','-',':']
		clrs=["red","blue","green","black","yellow"]
		markers=['o','v']
	 	ind=0
		for data in datas:
			plt.plot(datax[ind],data,label=labels[ind],color=clrs[ind],linestyle=linestyles[ind],linewidth=3)
			ind+=1
			plt.hold(True)
			plt.grid(True)
		plt.legend(loc=location,fontsize=fsize)
		plt.xlabel(xl,fontsize=fsize)
		plt.ylabel(yl,fontsize=fsize)
		plt.show()

	def plot_cdf(self,datas,labels,xl,yl,location,limit):
		fsize=18
		ax = figure().add_subplot(111)
		linestyles = ['-', ':', '--', '-.','-',':','--','-.']
		clrs=["red","green","blue","black","yellow","cyan","green","red"]
	 	ind=0
		for data in datas:
			data_sorted = np.sort(data)
			p = 1. * np.arange(len(data)) / (len(data) - 1)
			plt.plot(data_sorted,p,label=labels[ind],color=clrs[ind],linestyle=linestyles[ind],linewidth=3)
			if limit:
				plt.xlim(0,100)
			ind+=1
			plt.hold(True)
			plt.grid(True)
		for label in (ax.get_xticklabels() + ax.get_yticklabels()):
		    label.set_fontsize(fsize)		
		plt.legend(loc=location,fontsize=fsize)
		plt.title('', fontsize=fsize)
		plt.xlabel(xl,fontsize=fsize)
		plt.ylabel(yl,fontsize=fsize)
		plt.show()

	def plot_scatter(self,datas,labels,xl,yl):
		print len (datas)
		linestyles = ['-', ':', '--', '-.','-']
		clrs=["red","green"]
	 	ind=0
		plt.scatter(datas[0],datas[1],c="red")
		ind+=1
		plt.hold(True)
		plt.grid(True)
		plt.legend(loc=2,fontsize=10)
		plt.title('', fontsize=14)
		plt.xlabel(xl,fontsize=14)
		plt.ylabel(yl,fontsize=14)
		plt.show()

	def plot_hist(self,datas,labels,xl,colors,figtitle,n_bins):
		fsize=20
		ax = figure().add_subplot(111)
		for label in (ax.get_xticklabels() + ax.get_yticklabels()):
		    label.set_fontsize(fsize)
		plt.hist(datas, n_bins,normed=1,histtype='bar', color=colors, label=labels)
		plt.legend(prop={'size': fsize})
		plt.title(figtitle,fontsize=fsize)
		plt.xlabel(xl,fontsize =fsize)
		plt.ylabel('Normalized Frequency',fontsize=fsize)
		plt.show()		

	def get_hist(self,N,Means1,Std1,Means2,Std2,Means3,Std3,xlabels,tags):
		ind = np.arange(N)  # the x locations for the groups
		width = 0.25      # the width of the bars
		fig, ax = plt.subplots()
		rects1 = ax.bar(ind, Means1, width, color='r', yerr=Std1)
		rects2 = ax.bar(ind + width, Means2, width, color='w', yerr=Std2)
		rects3 = ax.bar(ind + width + width, Means3, width, color='w',hatch='//', yerr=Std3)
		ax.set_ylabel('Cost Reduction (%)')
		ax.set_xlabel('Slack (s)')
		ax.set_xticks(ind + width)
		ax.set_xticklabels(xlabels)
		ax.legend((rects1[0], rects2[0],rects3[0]), tags)
		ax = figure().add_subplot(111)
		for label in (ax.get_xticklabels() + ax.get_yticklabels()):
		    label.set_fontsize(fsize)

		def autolabel(rects):
		    for rect in rects:
		        height = rect.get_height()
		        ax.text(rect.get_x() + rect.get_width()/2., 1.05*height,
		                '%d' % int(height),
		                ha='center', va='bottom')
		autolabel(rects1)
		autolabel(rects2)
		autolabel(rects3)
		plt.show()


	def get_hist_no_err(self,N,Means1,Means2,Means3,xlabels,tags):
		ind = np.arange(N)  # the x locations for the groups
		width = 0.25      # the width of the bars
		fsize=18
		fig, ax = plt.subplots()
		rects1 = ax.bar(ind, Means1, width, color='r')
		rects2 = ax.bar(ind + width, Means2, width, color='w')
		rects3 = ax.bar(ind + width + width, Means3, width, color='w',hatch='//')
		# add some text for labels, title and axes ticks
		ax.set_ylabel('Price ($ / hr)',fontsize=fsize)
		ax.set_xlabel('Instance type',fontsize=fsize)
		ax.set_xticks(ind + width)
		ax.set_xticklabels(xlabels,rotation=30)
		ax.legend((rects1[0], rects2[0],rects3[0]), tags,fontsize=fsize,loc=2)
		for label in (ax.get_xticklabels() + ax.get_yticklabels()):
		    label.set_fontsize(16)

		plt.show()

