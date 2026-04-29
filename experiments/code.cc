/*
 * Copyright (c) 2026 GPRT
 *
 * Author: Maria Eduarda Veras <eduarda.martins@gprt.ufpe.br>
 * Author: Eduardo Freitas <eduardo.freitas@gprt.ufpe.br>
 *
 */

#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/traffic-control-module.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("L4SExample");

uint32_t checkTimes;
double avgQueueDiscSize;

Time rttFirst = Seconds(0);  // For Prague (n5)
Time rttSecond = Seconds(0); // For Cubic (n4)
uint32_t cwndFirst;          // For Prague (n5)
uint32_t cwndSecond;         // For Cubic (n4)
TcpSocketState::EcnState_t ecnStateFirst;
TcpSocketState::EcnState_t ecnStateSecond;

// The times
double global_start_time;
double global_stop_time;
double sink_start_time;
double sink_stop_time;
double client_start_time;
double client_stop_time;

NodeContainer n0n2;
NodeContainer n1n2;
NodeContainer n2n3;
NodeContainer n3n4;
NodeContainer n3n5;

Ipv4InterfaceContainer i0i2;
Ipv4InterfaceContainer i1i2;
Ipv4InterfaceContainer i2i3;
Ipv4InterfaceContainer i3i4;
Ipv4InterfaceContainer i3i5;

void TraceCwnd(std::ofstream *ofStream, uint32_t oldCwnd, uint32_t newCwnd)
{
    *ofStream << Simulator::Now().GetSeconds() << "," << newCwnd << std::endl;
}

void TraceRtt(std::ofstream *ofStream, Time oldRtt, Time newRtt)
{
    *ofStream << Simulator::Now().GetSeconds() << "," << newRtt.GetSeconds() << std::endl;
}

void TraceQueueProb(std::ofstream *stream, double oldVal, double newVal)
{
    *stream << Simulator::Now().GetSeconds() << " " << newVal << std::endl;
}

void TraceQueueSojourn(std::ofstream *stream, Time sojourn)
{
    *stream << Simulator::Now().GetSeconds() << " " << sojourn.GetSeconds() << std::endl;
}

void TraceQueueMark(std::ofstream *stream, Ptr<const QueueDiscItem> item, const char *reason)
{
    *stream << Simulator::Now().GetSeconds() << " " << reason << std::endl;
}

void ScheduleN4TraceConnections(std::ofstream *cwndStream, std::ofstream *rttStream)
{
    Config::ConnectWithoutContext("/NodeList/4/$ns3::TcpL4Protocol/SocketList/0/CongestionWindow",
                                  MakeBoundCallback(&TraceCwnd, cwndStream));
    Config::ConnectWithoutContext("/NodeList/4/$ns3::TcpL4Protocol/SocketList/0/RTT",
                                  MakeBoundCallback(&TraceRtt, rttStream));
}

void ScheduleN5TraceConnections(std::ofstream *cwndStream, std::ofstream *rttStream)
{
    Config::ConnectWithoutContext("/NodeList/5/$ns3::TcpL4Protocol/SocketList/0/CongestionWindow",
                                  MakeBoundCallback(&TraceCwnd, cwndStream));
    Config::ConnectWithoutContext("/NodeList/5/$ns3::TcpL4Protocol/SocketList/0/RTT",
                                  MakeBoundCallback(&TraceRtt, rttStream));
}

void MonitorThroughput(Ptr<FlowMonitor> flowMonitor,
                       Ptr<Ipv4FlowClassifier> classifier,
                       std::string filename)
{
    std::ofstream thrFile;
    thrFile.open(filename, std::ios::out | std::ios::app);

    flowMonitor->CheckForLostPackets();
    FlowMonitor::FlowStatsContainer stats = flowMonitor->GetFlowStats();

    // time, sourceIP, destinationIP, totalTxPkts, totalTxBytes, totalLostPkts,
    // deltaTxBits, deltaLostPkts
    for (auto i = stats.begin(); i != stats.end(); ++i)
    {
        Ipv4FlowClassifier::FiveTuple tuple = classifier->FindFlow(i->first);
        if (tuple.sourceAddress == "10.1.4.2")
        {
            thrFile << Simulator::Now().GetSeconds() << "," << tuple.sourceAddress << ","
                    << tuple.destinationAddress << "," << i->second.txPackets << ","
                    << i->second.txBytes << "," << i->second.txPackets - i->second.rxPackets
                    << "\n";
            thrFile.flush();
        }
        else if (tuple.sourceAddress == "10.1.5.2")
        {
            thrFile << Simulator::Now().GetSeconds() << "," << tuple.sourceAddress << ","
                    << tuple.destinationAddress << "," << i->second.txPackets << ","
                    << i->second.txBytes << "," << i->second.txPackets - i->second.rxPackets
                    << "\n";
            thrFile.flush();
        }
    }

    thrFile.close();

    Simulator::Schedule(Seconds(1), &MonitorThroughput, flowMonitor, classifier, filename);
}

void BuildAppsTest()
{
    uint16_t port1 = 50000;
    Address sinkLocalAddress1(InetSocketAddress(Ipv4Address::GetAny(), port1));
    PacketSinkHelper sinkHelper1("ns3::TcpSocketFactory", sinkLocalAddress1);
    ApplicationContainer sinkApp1 = sinkHelper1.Install(n0n2.Get(0));
    sinkApp1.Start(Seconds(sink_start_time));
    sinkApp1.Stop(Seconds(sink_stop_time));

    uint16_t port2 = 50001;
    Address sinkLocalAddress2(InetSocketAddress(Ipv4Address::GetAny(), port2));
    PacketSinkHelper sinkHelper2("ns3::TcpSocketFactory", sinkLocalAddress2);
    ApplicationContainer sinkApp2 = sinkHelper2.Install(n1n2.Get(0));
    sinkApp2.Start(Seconds(sink_start_time));
    sinkApp2.Stop(Seconds(sink_stop_time));

    Config::Set("/NodeList/0/$ns3::TcpL4Protocol/SocketType", TypeIdValue(TcpCubic::GetTypeId()));
    Config::Set("/NodeList/1/$ns3::TcpL4Protocol/SocketType", TypeIdValue(TcpPrague::GetTypeId()));
    Config::Set("/NodeList/4/$ns3::TcpL4Protocol/SocketType", TypeIdValue(TcpCubic::GetTypeId()));
    Config::Set("/NodeList/5/$ns3::TcpL4Protocol/SocketType", TypeIdValue(TcpPrague::GetTypeId()));

    // Connection one
    BulkSendHelper clientHelper1("ns3::TcpSocketFactory", Address());

    // Connection two
    BulkSendHelper clientHelper2("ns3::TcpSocketFactory", Address());

    ApplicationContainer clientApps1;
    AddressValue remoteAddress1(InetSocketAddress(i0i2.GetAddress(0), port1));
    clientHelper1.SetAttribute("Remote", remoteAddress1);
    clientApps1.Add(clientHelper1.Install(n3n4.Get(1)));
    clientApps1.Start(Seconds(client_start_time));
    clientApps1.Stop(Seconds(client_stop_time));

    ApplicationContainer clientApps2;
    AddressValue remoteAddress2(InetSocketAddress(i1i2.GetAddress(0), port2));
    clientHelper2.SetAttribute("Remote", remoteAddress2);
    clientApps2.Add(clientHelper2.Install(n3n5.Get(1)));
    clientApps2.Start(Seconds(client_start_time));
    clientApps2.Stop(Seconds(client_stop_time));
}

int main(int argc, char *argv[])
{
    std::string dualQCoupledPiSquareLinkDataRate = "10Mbps";
    std::string dualQCoupledPiSquareLinkDelay = "15ms";

    std::string pathOut;
    bool flowMonitor = true;

    bool printDualQCoupledPiSquareStats = true;

    global_start_time = 0.0;
    sink_start_time = global_start_time;
    client_start_time = global_start_time + 1.5;
    global_stop_time = 60.0;
    sink_stop_time = global_stop_time + 3.0;
    client_stop_time = global_stop_time - 2.0;

    // Configuration and command line parameter parsing
    // Will only save in the directory if enable opts below
    pathOut = "scratch/validation"; // Current directory
    CommandLine cmd;
    cmd.AddValue("pathOut",
                 "Path to save results from --writeForPlot/--writePcap/--writeFlowMonitor",
                 pathOut);
    cmd.AddValue("writeFlowMonitor",
                 "<0/1> to enable Flow Monitor and write their results",
                 flowMonitor);

    cmd.Parse(argc, argv);

    NS_LOG_INFO("Create nodes");
    NodeContainer c;
    c.Create(6);
    Names::Add("N0", c.Get(0));
    Names::Add("N1", c.Get(1));
    Names::Add("N2", c.Get(2));
    Names::Add("N3", c.Get(3));
    Names::Add("N4", c.Get(4));
    Names::Add("N5", c.Get(5));
    n0n2 = NodeContainer(c.Get(0), c.Get(2));
    n1n2 = NodeContainer(c.Get(1), c.Get(2));
    n2n3 = NodeContainer(c.Get(2), c.Get(3));
    n3n4 = NodeContainer(c.Get(3), c.Get(4));
    n3n5 = NodeContainer(c.Get(3), c.Get(5));

    Config::SetDefault("ns3::TcpSocketBase::UseEcn", StringValue("On"));
    Config::SetDefault("ns3::TcpDctcp::UseEct0", BooleanValue(false));
    Config::SetDefault("ns3::TcpSocket::SndBufSize",
                       UintegerValue(4194304)); // 4MB
    Config::SetDefault("ns3::TcpSocket::RcvBufSize",
                       UintegerValue(4194304)); // 4MB
    Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(1448));

    NS_LOG_INFO("Install internet stack on all nodes.");
    InternetStackHelper internet;
    internet.Install(c);

    TrafficControlHelper tchPfifo;
    uint16_t handle = tchPfifo.SetRootQueueDisc("ns3::PfifoFastQueueDisc");
    tchPfifo.AddInternalQueues(handle,
                               3,
                               "ns3::DropTailQueue",
                               "MaxSize",
                               QueueSizeValue(QueueSize("1000p")));

    TrafficControlHelper tchDualQCoupledPiSquare;
    handle = tchDualQCoupledPiSquare.SetRootQueueDisc("ns3::DualQCoupledPi2QueueDisc");

    // -----------------------------------------------------------------------

    NS_LOG_INFO("Create channels");
    PointToPointHelper p2p;

    NetDeviceContainer devn0n2;
    NetDeviceContainer devn1n2;
    NetDeviceContainer devn2n3;
    NetDeviceContainer devn3n4;
    NetDeviceContainer devn3n5;

    QueueDiscContainer queueDiscs;

    p2p.SetQueue("ns3::DropTailQueue");
    p2p.SetDeviceAttribute("DataRate", StringValue("1Gbps"));
    p2p.SetChannelAttribute("Delay", StringValue("0ms"));
    devn0n2 = p2p.Install(n0n2);
    tchPfifo.Install(devn0n2);

    p2p.SetQueue("ns3::DropTailQueue");
    p2p.SetDeviceAttribute("DataRate", StringValue("1Gbps"));
    p2p.SetChannelAttribute("Delay", StringValue("0ms"));
    devn1n2 = p2p.Install(n1n2);
    tchPfifo.Install(devn1n2);

    p2p.SetQueue("ns3::DropTailQueue", "MaxSize", StringValue("1p"));
    p2p.SetDeviceAttribute("DataRate", StringValue(dualQCoupledPiSquareLinkDataRate));
    p2p.SetChannelAttribute("Delay", StringValue(dualQCoupledPiSquareLinkDelay));
    devn2n3 = p2p.Install(n2n3);
    // only backbone link has DualQCoupledPiSquare queue disc
    queueDiscs.Add(tchDualQCoupledPiSquare.Install(devn2n3.Get(1)));
    tchPfifo.Install(devn2n3.Get(0));

    p2p.SetQueue("ns3::DropTailQueue");
    p2p.SetDeviceAttribute("DataRate", StringValue("1Gbps"));
    p2p.SetChannelAttribute("Delay", StringValue("0ms"));
    devn3n4 = p2p.Install(n3n4);
    tchPfifo.Install(devn3n4);

    p2p.SetQueue("ns3::DropTailQueue");
    p2p.SetDeviceAttribute("DataRate", StringValue("1Gbps"));
    p2p.SetChannelAttribute("Delay", StringValue("0ms"));
    devn3n5 = p2p.Install(n3n5);
    tchPfifo.Install(devn3n5);

    // -----------------------------------------------------------------------

    std::ofstream n4TcpCwndOfStream;
    n4TcpCwndOfStream.open(pathOut + "/cubic-cwnd.txt", std::ofstream::out);
    std::ofstream n4TcpRttOfStream;
    n4TcpRttOfStream.open(pathOut + "/cubic-rtt.txt", std::ofstream::out);

    std::ofstream n5TcpCwndOfStream;
    n5TcpCwndOfStream.open(pathOut + "/prague-cwnd.txt", std::ofstream::out);
    std::ofstream n5TcpRttOfStream;
    n5TcpRttOfStream.open(pathOut + "/prague-rtt.txt", std::ofstream::out);

    std::ofstream qProbCL, qProbC, qProbL, qSojournClassic, qSojournL4S, qMarks;

    qProbCL.open(pathOut + "/queue-prob-cl.txt", std::ios::out);
    qProbC.open(pathOut + "/queue-prob-c.txt", std::ios::out);
    qProbL.open(pathOut + "/queue-prob-l.txt", std::ios::out);
    qSojournClassic.open(pathOut + "/queue-sojourn-classic.txt", std::ios::out);
    qSojournL4S.open(pathOut + "/queue-sojourn-l4s.txt", std::ios::out);
    qMarks.open(pathOut + "/queue-marks.txt", std::ios::out);

    if (queueDiscs.GetN() > 0)
    {
        Ptr<QueueDisc> rootQ = queueDiscs.Get(0);
        Ptr<DualQCoupledPi2QueueDisc> dualQ = DynamicCast<DualQCoupledPi2QueueDisc>(rootQ);

        if (dualQ)
        {
            dualQ->TraceConnectWithoutContext("ProbCL",
                                              MakeBoundCallback(&TraceQueueProb, &qProbCL));
            dualQ->TraceConnectWithoutContext("ProbC", MakeBoundCallback(&TraceQueueProb, &qProbC));
            dualQ->TraceConnectWithoutContext("ProbL", MakeBoundCallback(&TraceQueueProb, &qProbL));

            dualQ->TraceConnectWithoutContext(
                "ClassicSojournTime",
                MakeBoundCallback(&TraceQueueSojourn, &qSojournClassic));
            dualQ->TraceConnectWithoutContext("L4sSojournTime",
                                              MakeBoundCallback(&TraceQueueSojourn, &qSojournL4S));

            dualQ->TraceConnectWithoutContext("Mark", MakeBoundCallback(&TraceQueueMark, &qMarks));
        }
    }
    // -----------------------------------------------------------------------

    NS_LOG_INFO("Assign IP Addresses");
    Ipv4AddressHelper ipv4;

    ipv4.SetBase("10.1.1.0", "255.255.255.0");
    i0i2 = ipv4.Assign(devn0n2);

    ipv4.SetBase("10.1.2.0", "255.255.255.0");
    i1i2 = ipv4.Assign(devn1n2);

    ipv4.SetBase("10.1.3.0", "255.255.255.0");
    i2i3 = ipv4.Assign(devn2n3);

    ipv4.SetBase("10.1.4.0", "255.255.255.0");
    i3i4 = ipv4.Assign(devn3n4);

    ipv4.SetBase("10.1.5.0", "255.255.255.0");
    i3i5 = ipv4.Assign(devn3n5);

    // Set up the routing
    Ipv4GlobalRoutingHelper::PopulateRoutingTables();

    FlowMonitorHelper flowmonHelper;
    Ptr<FlowMonitor> monitor = flowmonHelper.InstallAll();

    Simulator::Schedule(Seconds(client_start_time + 0.5),
                        &MonitorThroughput,
                        monitor,
                        DynamicCast<Ipv4FlowClassifier>(flowmonHelper.GetClassifier()),
                        pathOut + "/throughput.csv");

    BuildAppsTest();

    Simulator::Schedule(Seconds(client_start_time + 0.001),
                        &ScheduleN4TraceConnections,
                        &n4TcpCwndOfStream,
                        &n4TcpRttOfStream);

    Simulator::Schedule(Seconds(client_start_time + 0.001),
                        &ScheduleN5TraceConnections,
                        &n5TcpCwndOfStream,
                        &n5TcpRttOfStream);

    Simulator::Stop(Seconds(sink_stop_time));
    Simulator::Run();

    QueueDisc::Stats st = queueDiscs.Get(0)->GetStats();

    if (flowMonitor)
    {
        monitor->CheckForLostPackets();
        Ptr<Ipv4FlowClassifier> classifier =
            DynamicCast<Ipv4FlowClassifier>(flowmonHelper.GetClassifier());
        FlowMonitor::FlowStatsContainer stats = monitor->GetFlowStats();

        std::ofstream outFile;
        std::string summaryFilename = pathOut + "/flow_summary.txt";
        outFile.open(summaryFilename.c_str(), std::ofstream::out | std::ofstream::trunc);
        outFile.setf(std::ios_base::fixed);

        for (auto i = stats.begin(); i != stats.end(); ++i)
        {
            Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow(i->first);
            outFile << "Flow " << i->first << " (" << t.sourceAddress << ":" << t.sourcePort
                    << " -> " << t.destinationAddress << ":" << t.destinationPort << ") - " << "\n";
            outFile << "  Tx Packets: " << i->second.txPackets << "\n";
            outFile << "  Rx Packets: " << i->second.rxPackets << "\n";
            outFile << "  Throughput: "
                    << i->second.rxBytes * 8.0 / (client_stop_time - client_start_time) / 1024 /
                           1024
                    << " Mbps\n";
            outFile << "  Mean delay: " << i->second.delaySum.GetSeconds() / i->second.rxPackets
                    << " s\n";
        }
        outFile.close();
    }

    if (printDualQCoupledPiSquareStats)
    {
        std::cout << "*** DualQCoupledPiSquare stats from Node 3 queue ***" << std::endl;
        std::cout << "\t " << st << std::endl;
    }

    Simulator::Destroy();
    return 0;
}
