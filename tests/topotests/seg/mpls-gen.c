/*
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 */

#include <arpa/inet.h>
#include <linux/if_packet.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <net/if.h>
#include <netinet/ether.h>
#include <linux/mpls.h>
#include <netinet/ip.h>

#include <netdb.h>
#include <netinet/in.h>
#include <errno.h>
#include <net/if_arp.h>
#include <unistd.h>
#include <linux/netlink.h>
#include <linux/rtnetlink.h>

#define _GNU_SOURCE     /* To get defns of NI_MAXSERV and NI_MAXHOST */
#include <ifaddrs.h>
#include <linux/if_link.h>

#define BUF_SIZ		1024

#define BUFFER_SIZE 4096


//taken from https://gist.github.com/javiermon/6272065
//under http://www.apache.org/licenses/LICENSE-2.0
int getgatewayandiface(struct arpreq *req) {

	struct sockaddr_in* sin = (struct sockaddr_in*)&req->arp_pa;
	int     received_bytes = 0, msg_len = 0, route_attribute_len = 0;
	int     sock = -1, msgseq = 0;
	struct  nlmsghdr *nlh, *nlmsg;
	struct  rtmsg *route_entry;
	// This struct contain route attributes (route type)
	struct  rtattr *route_attribute;
	char    gateway_address[INET_ADDRSTRLEN];
	
	char    msgbuf[BUFFER_SIZE], buffer[BUFFER_SIZE];
	char    *ptr = buffer;
	struct timeval tv = {0};

	if ((sock = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE)) < 0) {
		perror("socket failed");
		return -1;
	}

	memset(msgbuf, 0, sizeof(msgbuf));
	memset(buffer, 0, sizeof(buffer));

	/* point the header and the msg structure pointers into the buffer */
	nlmsg = (struct nlmsghdr *)msgbuf;

	/* Fill in the nlmsg header*/
	nlmsg->nlmsg_len = NLMSG_LENGTH(sizeof(struct rtmsg));
	nlmsg->nlmsg_type = RTM_GETROUTE; // Get the routes from kernel routing table .
	nlmsg->nlmsg_flags = NLM_F_DUMP | NLM_F_REQUEST; // The message is a request for dump.
	nlmsg->nlmsg_seq = msgseq++; // Sequence of the message packet.
	nlmsg->nlmsg_pid = getpid(); // PID of process sending the request.

	/* 1 Sec Timeout to avoid stall */
	tv.tv_sec = 1;
	setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (struct timeval *)&tv, sizeof(struct timeval));
	/* send msg */
	if (send(sock, nlmsg, nlmsg->nlmsg_len, 0) < 0) {
		perror("send failed");
		return -1;
	}

	/* receive response */
	do
	{
		received_bytes = recv(sock, ptr, sizeof(buffer) - msg_len, 0);
		if (received_bytes < 0) {
			perror("Error in recv");
			return -1;
		}

		nlh = (struct nlmsghdr *) ptr;

		/* Check if the header is valid */
		if((NLMSG_OK(nlmsg, received_bytes) == 0) ||
		   (nlmsg->nlmsg_type == NLMSG_ERROR))
		{
			perror("Error in received packet");
			return -1;
		}

		/* If we received all data break */
		if (nlh->nlmsg_type == NLMSG_DONE)
			break;
		else {
			ptr += received_bytes;
			msg_len += received_bytes;
		}

		/* Break if its not a multi part message */
		if ((nlmsg->nlmsg_flags & NLM_F_MULTI) == 0)
			break;
	}
	while ((nlmsg->nlmsg_seq != msgseq) || (nlmsg->nlmsg_pid != getpid()));

	/* parse response */
	for ( ; NLMSG_OK(nlh, received_bytes); nlh = NLMSG_NEXT(nlh, received_bytes))
	{
		/* Get the route data */
		route_entry = (struct rtmsg *) NLMSG_DATA(nlh);

		/* We are just interested in main routing table */
		if (route_entry->rtm_table != RT_TABLE_MAIN)
			continue;

		route_attribute = (struct rtattr *) RTM_RTA(route_entry);
		route_attribute_len = RTM_PAYLOAD(nlh);

		/* Loop through all attributes */
		for ( ; RTA_OK(route_attribute, route_attribute_len);
			  route_attribute = RTA_NEXT(route_attribute, route_attribute_len))
		{
			switch(route_attribute->rta_type) {
			case RTA_OIF:
				if_indextoname(*(int *)RTA_DATA(route_attribute), req->arp_dev);
				// printf("\tIDX:%d\n",*(int *)RTA_DATA(route_attribute));
				break;
			case RTA_GATEWAY:
				sin->sin_addr.s_addr = *(in_addr_t*)RTA_DATA(route_attribute);
				sin->sin_family = AF_INET;
				inet_ntop(AF_INET, RTA_DATA(route_attribute),
						gateway_address, sizeof(gateway_address));
				// printf("\tintf: %s\n",gateway_address);
				break;
			case RTA_PRIORITY:
				// printf("\tPRIORITY:%d \n",*(int *)RTA_DATA(route_attribute));
				break;
			default:
				break;
			}
			
			if ((sin->sin_addr.s_addr) && (*req->arp_dev)) {
				//printf("%s\n",req->arp_dev );
				// break;
			} 
		}
		// printf("next message: \n");
	}

	close(sock);
	sock = -1;


	if ((sock = socket(AF_INET, SOCK_DGRAM, 0)) < 0)
	{
		printf("socket() failed.");
		return -1;
	} /* Socket is opened.*/


	if (ioctl(sock, SIOCGARP, (caddr_t)req) < 0)
	{
		printf("ioctl() failed.");
		return -1;
	}
	close(sock); /* Close the socket, we don't need it anymore. */

	return 0;
}

int append_mpls(void * sendbuf, int tx_len, 
	int lbl, 
	int exp, 
	int lst, 
	int ttl){

	uint32_t mplsFrame = 0;
	mplsFrame |= (lbl << MPLS_LS_LABEL_SHIFT ) & MPLS_LS_LABEL_MASK;
	mplsFrame |= (exp << MPLS_LS_TC_SHIFT    ) & MPLS_LS_TC_MASK;
	mplsFrame |= (lst << MPLS_LS_S_SHIFT     ) & MPLS_LS_S_MASK;
	mplsFrame |= (ttl << MPLS_LS_TTL_SHIFT   ) & MPLS_LS_TTL_MASK;


	*(uint8_t*)(sendbuf + tx_len++) = (mplsFrame >> 24) & 0xFF;
	*(uint8_t*)(sendbuf + tx_len++) = (mplsFrame >> 16) & 0xFF;
	*(uint8_t*)(sendbuf + tx_len++) = (mplsFrame >>  8) & 0xFF;
	*(uint8_t*)(sendbuf + tx_len++) = (mplsFrame >>  0) & 0xFF;

	return sizeof mplsFrame;

}

void getIP(){
	struct ifaddrs *ifaddr;
	int family, s;
	char host[NI_MAXHOST];

	if (getifaddrs(&ifaddr) == -1) {
		perror("getifaddrs");
		exit(EXIT_FAILURE);
	}

	/* Walk through linked list, maintaining head pointer so we
		can free list later. */

	for (struct ifaddrs *ifa = ifaddr; ifa != NULL;
			ifa = ifa->ifa_next) {
		if (ifa->ifa_addr == NULL)
			continue;

		family = ifa->ifa_addr->sa_family;

		/* Display interface name and family (including symbolic
			form of the latter for the common families). */

		printf("%-8s %s (%d)\n",
				ifa->ifa_name,
				(family == AF_PACKET) ? "AF_PACKET" :
				(family == AF_INET) ? "AF_INET" :
				(family == AF_INET6) ? "AF_INET6" : "???",
				family);

		/* For an AF_INET* interface address, display the address. */

		if (family == AF_INET || family == AF_INET6) {
			s = getnameinfo(ifa->ifa_addr,
					(family == AF_INET) ? sizeof(struct sockaddr_in) :
											sizeof(struct sockaddr_in6),
					host, NI_MAXHOST,
					NULL, 0, NI_NUMERICHOST);
			if (s != 0) {
				printf("getnameinfo() failed: %s\n", gai_strerror(s));
				exit(EXIT_FAILURE);
			}

			printf("\t\taddress: <%s>\n", host);

		} else if (family == AF_PACKET && ifa->ifa_data != NULL) {
			struct rtnl_link_stats *stats = ifa->ifa_data;

			printf("\t\ttx_packets = %10u; rx_packets = %10u\n"
					"\t\ttx_bytes   = %10u; rx_bytes   = %10u\n",
					stats->tx_packets, stats->rx_packets,
					stats->tx_bytes, stats->rx_bytes);
		}
	}

	freeifaddrs(ifaddr);
	exit(EXIT_SUCCESS);
}


char *mac_ntoa(unsigned char *ptr)
{
    static char address[30];
    sprintf(address, "%02X:%02X:%02X:%02X:%02X:%02X",
            ptr[0], ptr[1], ptr[2], ptr[3], ptr[4], ptr[5]);
    return (address);
}


int main(int argc, char *argv[])
{
	int sockfd;
	struct ifreq if_idx;
	struct ifreq if_mac;
	int tx_len = 0;
	char sendbuf[BUF_SIZ];
	struct ether_header *eh = (struct ether_header *) sendbuf;
	struct ip *iph;// = (struct iphdr *) (sendbuf + sizeof(struct ether_header));
	struct sockaddr_ll socket_address;
	struct arpreq req = {0};

	uint16_t *labels = malloc (sizeof(uint16_t) * (argc - 1));

	for (int i = 0; i < (argc -1); i++){
		labels[i] = strtol(argv[i + 1], NULL, 0);
	}

	//obtain defualt gateway destination  mac address and interface name
	if (getgatewayandiface(&req) < 0) {
		printf("error encountered 1\n");
	}

	/* Open RAW socket to send on */
	if ((sockfd = socket(AF_PACKET, SOCK_RAW, IPPROTO_RAW)) == -1) {
		perror("socket");
	}

	/* Get the index of the interface to send on */
	memset(&if_idx, 0, sizeof(struct ifreq));
	strncpy(if_idx.ifr_name, req.arp_dev, IFNAMSIZ-1);
	if (ioctl(sockfd, SIOCGIFINDEX, &if_idx) < 0)
		perror("SIOCGIFINDEX");
	/* Get the MAC address of the interface to send on */
	memset(&if_mac, 0, sizeof(struct ifreq));
	strncpy(if_mac.ifr_name, req.arp_dev, IFNAMSIZ-1);
	if (ioctl(sockfd, SIOCGIFHWADDR, &if_mac) < 0)
		perror("SIOCGIFHWADDR");

	if (ioctl(sockfd, SIOCGIFADDR, &if_mac) < 0)
		perror("SIOCGIFADDR");

	printf("ADDR DST/SRC: %s\n", inet_ntoa(
		((struct sockaddr_in *)&if_mac.ifr_addr )->sin_addr));


	//we have all the information now, need to construct packet

	//Ethernet frame
	//MPLS frame
	//IPv4 frame
	//UDP frame

	/* Construct the Ethernet header */
	memset(sendbuf, 0, BUF_SIZ);
	/* Ethernet header */
	eh->ether_shost[0] = if_mac.ifr_hwaddr.sa_data[0];
	eh->ether_shost[1] = if_mac.ifr_hwaddr.sa_data[1];
	eh->ether_shost[2] = if_mac.ifr_hwaddr.sa_data[2];
	eh->ether_shost[3] = if_mac.ifr_hwaddr.sa_data[3];
	eh->ether_shost[4] = if_mac.ifr_hwaddr.sa_data[4];
	eh->ether_shost[5] = if_mac.ifr_hwaddr.sa_data[5];
	eh->ether_dhost[0] = req.arp_ha.sa_data[0];
	eh->ether_dhost[1] = req.arp_ha.sa_data[1];
	eh->ether_dhost[2] = req.arp_ha.sa_data[2];
	eh->ether_dhost[3] = req.arp_ha.sa_data[3];
	eh->ether_dhost[4] = req.arp_ha.sa_data[4];
	eh->ether_dhost[5] = req.arp_ha.sa_data[5];


	printf("Found SRC MAC: %s\n", mac_ntoa(eh->ether_shost));
	printf("Found DST MAC: %s\n", mac_ntoa(eh->ether_dhost));


	/* Ethertype field */
	//from if_ether.h
	//#define ETH_P_MPLS_UC 0x8847 /* MPLS Unicast traffic   */
	//#define ETH_P_MPLS_MC 0x8848 /* MPLS Multicast traffic */

	eh->ether_type = htons(ETH_P_MPLS_UC);
	//eh->ether_type = htons(ETH_P_IP);
	tx_len += sizeof(struct ether_header);

	// tx_len += append_mpls(sendbuf, tx_len, 20014, 0, 0, 64);
	// tx_len += append_mpls(sendbuf, tx_len, 5003, 0, 0, 64);
	// tx_len += append_mpls(sendbuf, tx_len, 20001, 0, 1, 64);

	for (int i = 0; i < (argc-1); i++){
		tx_len += append_mpls(sendbuf, tx_len, labels[i], 0, (argc -2) == i ? 1 : 0, 64);
	}

	free(labels);

	iph = (struct ip *) (sendbuf + tx_len);
	tx_len += sizeof *iph;

	iph->ip_v =  4;
	iph->ip_hl = 5;
	iph->ip_tos = 0;
	
	iph->ip_id = 0;
	iph->ip_off = htons(0x4000);
	iph->ip_ttl = 64; 
	iph->ip_p = 17; //UDP

	iph->ip_src = ((struct sockaddr_in *)&if_mac.ifr_addr )->sin_addr;
	iph->ip_dst = ((struct sockaddr_in *)&if_mac.ifr_addr )->sin_addr;



	struct udp {
		uint16_t src;
		uint16_t dst;
		uint16_t length;
		uint16_t checksum;

		uint16_t payload;
	};


	sendbuf[tx_len++] = 0x00; //src port
	sendbuf[tx_len++] = 0x00;
	sendbuf[tx_len++] = 0; //dst port
	sendbuf[tx_len++] = 88;

	sendbuf[tx_len++] = 0x00; //length
	sendbuf[tx_len++] = 0x08;
	sendbuf[tx_len++] = 0x00; //checksum
	sendbuf[tx_len++] = 0x00;
	sendbuf[tx_len++] = 0xFF; //payload
	sendbuf[tx_len++] = 0xFF;

	uint16_t len = tx_len - ( (void *)iph - (void *)sendbuf);
	iph->ip_len = htons(len);

	uint32_t sum = 
		(uint32_t)0 +
		((uint16_t *)iph)[0] +
		((uint16_t *)iph)[1] +
		((uint16_t *)iph)[2] +
		((uint16_t *)iph)[3] +
		((uint16_t *)iph)[4] +

		((uint16_t *)iph)[6] +
		((uint16_t *)iph)[7] +
		((uint16_t *)iph)[8] +
		((uint16_t *)iph)[9];
	sum = (sum&0xffff) + (sum>>16);
	sum = (sum&0xffff) + (sum>>16);
	sum = ~sum;

	iph->ip_sum = sum;


	/* Index of the network device */
	socket_address.sll_ifindex = if_idx.ifr_ifindex;
	/* Address length*/
	socket_address.sll_halen = ETH_ALEN;

	/* Send packet */
	if (sendto(sockfd, sendbuf, tx_len, 0, (struct sockaddr*)&socket_address, sizeof(struct sockaddr_ll)) < 0)
		printf("Send failed\n");



	return 0;
}


