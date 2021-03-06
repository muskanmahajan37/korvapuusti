
#include "../carfac.h"

#include <stdio.h>

#include "../carfac/cpp/carfac.h"

carfac create_carfac(int sample_rate) {
  CARParams car_params;
  IHCParams ihc_params;
  AGCParams agc_params;
  auto c = new CARFAC(1, static_cast<float>(sample_rate), car_params,
                      ihc_params, agc_params);
  return carfac{
    c,
    new CARFACOutput(true, true, false, false),
    // We aren't interested in frequencies below 20Hz.
    static_cast<int>(sample_rate / 10),
    sample_rate,
    c->num_channels(),
    {
      c->num_channels(),
      c->pole_frequencies().data(),
    },
  };
}

void delete_carfac(carfac *cf) { delete static_cast<CARFAC *>(cf->cf); }

void carfac_run(carfac *cf, float_ary buffer) {
  auto real_cf = static_cast<CARFAC *>(cf->cf);
  real_cf->Reset();
  auto input_map = ArrayXX::Map(reinterpret_cast<const float *>(buffer.data), 1,
                                cf->num_samples);
  auto real_output = static_cast<CARFACOutput *>(cf->latest_output);
  real_cf->RunSegment(input_map, false, real_output);
}

int carfac_bm(carfac *cf, float_ary result) {
  if (result.len != cf->num_samples * cf->num_channels) {
    return -1;
  }

  auto real_output = static_cast<CARFACOutput *>(cf->latest_output);
  memcpy(result.data, real_output->bm()[0].data(), sizeof(float) * result.len);

  return 0;
}

int carfac_nap(carfac *cf, float_ary result) {
  if (result.len != cf->num_samples * cf->num_channels) {
    return -1;
  }

  auto real_output = static_cast<CARFACOutput *>(cf->latest_output);
  memcpy(result.data, real_output->nap()[0].data(), sizeof(float) * result.len);

  return 0;
}
