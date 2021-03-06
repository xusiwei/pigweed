// Copyright 2020 The Pigweed Authors
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not
// use this file except in compliance with the License. You may obtain a copy of
// the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
// WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
// License for the specific language governing permissions and limitations under
// the License.

// These tests call the pw_thread module sleep API from C. The return values are
// checked in the main C++ tests.

#include "pw_thread/sleep.h"

void pw_this_thread_CallSleepFor(
    pw_chrono_SystemClock_Duration sleep_duration) {
  pw_this_thread_SleepFor(sleep_duration);
}

void pw_this_thread_CallSleepUntil(
    pw_chrono_SystemClock_TimePoint wakeup_time) {
  pw_this_thread_SleepUntil(wakeup_time);
}
