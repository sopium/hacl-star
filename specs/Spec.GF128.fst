module Spec.GF128

open FStar.Mul
open Lib.IntTypes
open Lib.Sequence
open Lib.ByteSequence
open Spec.GaloisField
open Lib.LoopCombinators

(* Field types and parameters *)

let gf128 = mk_field 128 0xe1000000000000000000000000000000
let elem = felem gf128
let zero = zero #gf128

(* GCM types and specs *)
let blocksize : size_nat = 16
let keysize   : size_nat = 16
type block = lbytes blocksize
type tag   = lbytes blocksize
type key   = lbytes keysize

let encode (len:size_nat{len <= blocksize}) (w:lbytes len) : Tot elem =
  let b = create blocksize (u8 0) in
  let b = update_slice b 0 len w  in
  to_felem (nat_from_bytes_be b)

let decode (e:elem) : Tot block = nat_to_bytes_be blocksize (from_felem e)

let update (r:elem ) (len:size_nat{len <= blocksize}) (w:lbytes len) (acc:elem) : Tot elem =
    (encode len w `fadd` acc) `fmul` r

let poly (text:seq uint8) (r:elem) =
  repeat_blocks #uint8 #elem blocksize text
    (fun i b -> update r blocksize b)
    (fun i -> update r)
  zero

let finish (a:elem) (s:tag) : Tot tag = decode (a `fadd` (encode blocksize s))

let gmul (text:bytes) (h:lbytes blocksize) : Tot tag  =
    let r = encode blocksize h in
    decode (poly text r)

val gmac:
  text:bytes ->
  h:lbytes blocksize ->
  k:key ->
  Tot tag
let gmac text h k =
  let r = encode blocksize h in
  finish (poly text r) k
