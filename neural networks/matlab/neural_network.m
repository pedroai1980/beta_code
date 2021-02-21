%the dataset must exist in the workspace
mu=mean(data)
sig=std(data)

T=num2cell((data-mu)/sig,1)
net = narnet(1:3,10);
[Xs,Xi,Ai,Ts] = preparets(net,{},{},T);
net = train(net,Xs,Ts,Xi,Ai);

[Y,Xf,Af] = net(Xs,Xi,Ai);
perf = perform(net,Ts,Y)
[netc,Xic,Aic] = closeloop(net,Xf,Af);

y2 = netc(cell(0,12),Xic,Aic)
result=cell2mat(y2)
result= result*sig+mu
plot(result)
