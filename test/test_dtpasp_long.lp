
0.3::a(0).
0.3::a(1).
0.3::a(2).
0.3::a(3).
0.3::a(4).
0.3::a(5).
0.3::a(6).
0.3::a(7).
0.3::a(8).
0.3::a(9).

?::da(0).

qr:- a(0), da(0).
qr :- a(1), da(0), \+ nqr.
nqr :- a(1), da(0), \+ qr.
qr:- a(2), da(0).
qr :- a(3), da(0), \+ nqr.
nqr :- a(3), da(0), \+ qr.
qr:- a(4), da(0).
qr :- a(5), da(0), \+ nqr.
nqr :- a(5), da(0), \+ qr.
qr:- a(6), da(0).
qr :- a(7), da(0), \+ nqr.
nqr :- a(7), da(0), \+ qr.
qr:- a(8), da(0).
qr :- a(9), da(0), \+ nqr.
nqr :- a(9), da(0), \+ qr.

utility(qr,2).
utility(nqr,-12).

