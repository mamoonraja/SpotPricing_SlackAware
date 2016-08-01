
zonelist='us-east-1 eu-west-1 ap-northeast-1'
itype='m3.medium m4.large'
for typ in $itype;do
	for zone in $zonelist;do
	        echo $zone
	        mkdir $typ
			export AWS_DEFAULT_REGION=$zone
			aws ec2 describe-spot-price-history --instance-types $typ --product-description "Linux/UNIX (Amazon VPC)" --start-time 2016-04-22T00:00:00 --end-time 2016-06-22T23:09:10 > ./$typ/$zone.json
	done
done
