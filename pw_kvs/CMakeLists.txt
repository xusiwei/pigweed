# Copyright 2020 The Pigweed Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

include($ENV{PW_ROOT}/pw_build/pigweed.cmake)

pw_add_module_config(pw_kvs_CONFIG)

pw_auto_add_simple_module(pw_kvs
  PUBLIC_DEPS
    pw_containers
    pw_status
    pw_sync.borrow
  PRIVATE_DEPS
    pw_assert
    pw_bytes
    pw_checksum
    ${pw_kvs_CONFIG}
    pw_log
    pw_random
    pw_stream
    pw_string
)

target_compile_definitions(
  pw_kvs
  PUBLIC PW_FLASH_TEST_SECTORS=6
  PUBLIC PW_FLASH_TEST_SECTOR_SIZE=4096
  PUBLIC PW_FLASH_TEST_ALIGNMENT=1
  PUBLIC PW_FLASH_TEST_ITERATIONS=2
  PUBLIC PW_FLASH_TEST_WRITE_SIZE=256
)
