0.3::a(0).
?::da(0).
?::da(1).
qr:- a(0), da(0).
qr :- a(0), da(1), \+ nqr.
nqr :- a(0), da(1), \+ qr.
utility(qr,2).
utility(nqr,-12).
