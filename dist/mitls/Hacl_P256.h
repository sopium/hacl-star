/* MIT License
 *
 * Copyright (c) 2016-2020 INRIA, CMU and Microsoft Corporation
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

#include "evercrypt_targetconfig.h"
#include "lib_intrinsics.h"
#include "libintvector.h"
#include "kremlin/internal/types.h"
#include "kremlin/lowstar_endianness.h"
#include <string.h>
#include "kremlin/internal/target.h"

#ifndef __Hacl_P256_H
#define __Hacl_P256_H

#include "Hacl_Kremlib.h"
#include "Hacl_Hash.h"
#include "Hacl_Spec.h"


uint64_t Hacl_Impl_P256_LowLevel_sub4_il(uint64_t *x, const uint64_t *y, uint64_t *result);

void Hacl_Impl_P256_LowLevel_shift_256_impl(uint64_t *i, uint64_t *o);

void Hacl_Impl_P256_LowLevel_toUint8(uint64_t *i, uint8_t *o);

void Hacl_Impl_P256_LowLevel_changeEndian(uint64_t *i);

void Hacl_Impl_P256_LowLevel_toUint64ChangeEndian(uint8_t *i, uint64_t *o);

void
Hacl_Impl_ECDSA_MontgomeryMultiplication_reduction_prime_2prime_order(
  uint64_t *x,
  uint64_t *result
);

extern const uint64_t Hacl_Impl_P256_LowLevel_PrimeSpecific_prime256_buffer[4U];

void Hacl_Impl_SolinasReduction_solinas_reduction_impl(uint64_t *i, uint64_t *o);

void
Hacl_Impl_P256_PointAdd_point_add(
  uint64_t *p,
  uint64_t *q,
  uint64_t *result,
  uint64_t *tempBuffer
);

void Hacl_Impl_P256_Core_norm(uint64_t *p, uint64_t *resultPoint, uint64_t *tempBuffer);

void
Hacl_Impl_P256_Core_scalarMultiplicationWithoutNorm(
  uint64_t *p,
  uint64_t *result,
  uint8_t *scalar,
  uint64_t *tempBuffer
);

void
Hacl_Impl_P256_Core_secretToPublicWithoutNorm(
  uint64_t *result,
  uint8_t *scalar,
  uint64_t *tempBuffer
);

void Hacl_Impl_P256_Signature_Common_bufferToJac(uint64_t *p, uint64_t *result);

bool Hacl_Impl_P256_Signature_Common_isPointAtInfinityPublic(uint64_t *p);

bool
Hacl_Impl_P256_Signature_Common_verifyQValidCurvePoint(
  uint64_t *pubKeyAsPoint,
  uint64_t *tempBuffer
);

uint64_t Hacl_Impl_P256_DH_ecp256dh_i(uint8_t *result, uint8_t *scalar);

uint64_t Hacl_Impl_P256_DH_ecp256dh_r(uint8_t *result, uint8_t *pubKey, uint8_t *scalar);

void Hacl_Impl_P256_Compression_computeYFromX(uint64_t *x, uint64_t *result, uint64_t sign);

void Hacl_Impl_ECDSA_MM_Exponent_montgomery_ladder_exponent(uint64_t *r);

void Hacl_Impl_ECDSA_MM_Exponent_fromDomainImpl(uint64_t *a, uint64_t *result);

void
Hacl_Impl_ECDSA_MM_Exponent_multPowerPartial(
  uint64_t *s,
  uint64_t *a,
  uint64_t *b,
  uint64_t *result
);

bool Hacl_Impl_ECDSA_P256_Verification_Agile_isMoreThanZeroLessThanOrderMinusOne(uint64_t *f);

bool Hacl_Impl_ECDSA_P256_Verification_Agile_compare_felem_bool(uint64_t *a, uint64_t *b);

uint64_t
Hacl_Impl_ECDSA_P256_Signature_Agile_ecdsa_signature_core(
  Spec_ECDSA_hash_alg_ecdsa alg,
  uint64_t *r,
  uint64_t *s,
  uint32_t mLen,
  uint8_t *m,
  uint64_t *privKeyAsFelem,
  uint8_t *k
);

uint64_t
Hacl_Interface_P256_ecdsa_sign_p256_sha2(
  uint8_t *result,
  uint32_t mLen,
  uint8_t *m,
  uint8_t *privKey,
  uint8_t *k
);

uint64_t
Hacl_Interface_P256_ecdsa_sign_p256_sha384(
  uint8_t *result,
  uint32_t mLen,
  uint8_t *m,
  uint8_t *privKey,
  uint8_t *k
);

uint64_t
Hacl_Interface_P256_ecdsa_sign_p256_sha512(
  uint8_t *result,
  uint32_t mLen,
  uint8_t *m,
  uint8_t *privKey,
  uint8_t *k
);

uint64_t
Hacl_Interface_P256_ecdsa_sign_p256_without_hash(
  uint8_t *result,
  uint32_t mLen,
  uint8_t *m,
  uint8_t *privKey,
  uint8_t *k
);

bool
Hacl_Interface_P256_ecdsa_verif_p256_sha2(
  uint32_t mLen,
  uint8_t *m,
  uint8_t *pubKey,
  uint8_t *r,
  uint8_t *s
);

bool
Hacl_Interface_P256_ecdsa_verif_p256_sha384(
  uint32_t mLen,
  uint8_t *m,
  uint8_t *pubKey,
  uint8_t *r,
  uint8_t *s
);

bool
Hacl_Interface_P256_ecdsa_verif_p256_sha512(
  uint32_t mLen,
  uint8_t *m,
  uint8_t *pubKey,
  uint8_t *r,
  uint8_t *s
);

bool
Hacl_Interface_P256_ecdsa_verif_without_hash(
  uint32_t mLen,
  uint8_t *m,
  uint8_t *pubKey,
  uint8_t *r,
  uint8_t *s
);

bool Hacl_Interface_P256_verify_q(uint8_t *pubKey);

bool Hacl_Interface_P256_decompression_not_compressed_form(uint8_t *b, uint8_t *result);

bool Hacl_Interface_P256_decompression_compressed_form(uint8_t *b, uint8_t *result);

void Hacl_Interface_P256_compression_not_compressed_form(uint8_t *b, uint8_t *result);

void Hacl_Interface_P256_compression_compressed_form(uint8_t *b, uint8_t *result);

void Hacl_Interface_P256_reduction_8_32(uint8_t *x, uint8_t *result);

uint64_t Hacl_Interface_P256_ecp256dh_i(uint8_t *result, uint8_t *scalar);

uint64_t Hacl_Interface_P256_ecp256dh_r(uint8_t *result, uint8_t *pubKey, uint8_t *scalar);

#define __Hacl_P256_H_DEFINED
#endif
