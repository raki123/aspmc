0.3::a(0).
0.3::a(1).
?::da(0).
qr:- a(0), da(0).
qr :- a(1), da(0), \+ nqr.
nqr :- a(1), da(0), \+ qr.
utility(qr,2).
utility(nqr,-12).
