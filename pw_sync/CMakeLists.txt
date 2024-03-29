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

pw_add_facade(pw_sync.binary_semaphore
  HEADERS
    public/pw_sync/binary_semaphore.h
  PUBLIC_INCLUDES
    public
  PUBLIC_DEPS
    pw_chrono.system_clock
    pw_preprocessor
  SOURCES
    binary_semaphore.cc
)

pw_add_facade(pw_sync.counting_semaphore
  HEADERS
    public/pw_sync/counting_semaphore.h
  PUBLIC_INCLUDES
    public
  PUBLIC_DEPS
    pw_chrono.system_clock
    pw_preprocessor
  SOURCES
    counting_semaphore.cc
)

pw_add_module_library(pw_sync.lock_annotations
  HEADERS
    public/pw_sync/lock_annotations.h
  PUBLIC_INCLUDES
    public
  PUBLIC_DEPS
    pw_preprocessor
)

pw_add_module_library(pw_sync.borrow
  HEADERS
    public/pw_sync/borrow.h
  PUBLIC_INCLUDES
    public
  PUBLIC_DEPS
    pw_assert
    pw_sync.lock_annotations
    pw_sync.virtual_basic_lockable
)

pw_add_module_library(pw_sync.virtual_basic_lockable
  HEADERS
    public/pw_sync/virtual_basic_lockable.h
  PUBLIC_INCLUDES
    public
  PUBLIC_DEPS
    pw_polyfill
    pw_sync.lock_annotations
)

pw_add_facade(pw_sync.mutex
  HEADERS
    public/pw_sync/mutex.h
  PUBLIC_INCLUDES
    public
  PUBLIC_DEPS
    pw_sync.lock_annotations
    pw_sync.virtual_basic_lockable
    pw_preprocessor
  SOURCES
    mutex.cc
)

pw_add_facade(pw_sync.timed_mutex
  HEADERS
    public/pw_sync/timed_mutex.h
  PUBLIC_INCLUDES
    public
  PUBLIC_DEPS
    pw_chrono.system_clock
    pw_preprocessor
    pw_sync.mutex
    pw_sync.virtual_basic_lockable
  SOURCES
    timed_mutex.cc
)

pw_add_facade(pw_sync.interrupt_spin_lock
  HEADERS
    public/pw_sync/interrupt_spin_lock.h
  PUBLIC_INCLUDES
    public
  PUBLIC_DEPS
    pw_sync.lock_annotations
    pw_sync.virtual_basic_lockable
    pw_preprocessor
  SOURCES
    interrupt_spin_lock.cc
)

pw_add_facade(pw_sync.thread_notification
  HEADERS
    public/pw_sync/thread_notification.h
  PUBLIC_INCLUDES
    public
)

pw_add_facade(pw_sync.timed_thread_notification
  HEADERS
    public/pw_sync/timed_thread_notification.h
  PUBLIC_INCLUDES
    public
  PUBLIC_DEPS
    pw_sync.thread_notification
    pw_chrono.system_clock
)

# This target provides the backend for pw::sync::ThreadNotification based on
# pw::sync::BinarySemaphore.
pw_add_module_library(pw_sync.binary_semaphore_thread_notification_backend
  HEADERS
    public/pw_sync/backends/binary_semaphore_thread_notification_inline.h
    public/pw_sync/backends/binary_semaphore_thread_notification_native.h
    public_overrides/pw_sync_backend/thread_notification_inline.h
    public_overrides/pw_sync_backend/thread_notification_native.h
  PUBLIC_INCLUDES
    public
    public_overrides
  PUBLIC_DEPS
    pw_sync.binary_semaphore
)

# This target provides the backend for pw::sync::TimedThreadNotification based
# on pw::sync::BinarySemaphore.
pw_add_module_library(pw_sync.binary_semaphore_timed_thread_notification_backend
  HEADERS
    public/pw_sync/backends/binary_semaphore_timed_thread_notification_inline.h
    public_overrides/pw_sync_backend/timed_thread_notification_inline.h
  PUBLIC_INCLUDES
    public
    public_overrides
  PUBLIC_DEPS
    pw_chrono.system_clock
    pw_sync.binary_semaphore_thread_notification_backend
)

pw_add_module_library(pw_sync.yield_core
  HEADERS
    public/pw_sync/yield_core.h
  PUBLIC_INCLUDES
    public
)

pw_add_test(pw_sync.borrow_test
  SOURCES
    borrow_test.cc
  DEPS
    pw_assert
    pw_sync.borrow
    pw_sync.virtual_basic_lockable
  GROUPS
    modules
    pw_sync
)

if(NOT "${pw_sync.binary_semaphore_BACKEND}" STREQUAL
   "pw_sync.binary_semaphore.NO_BACKEND_SET")
  pw_add_test(pw_sync.binary_semaphore_facade_test
    SOURCES
      binary_semaphore_facade_test.cc
      binary_semaphore_facade_test_c.c
    DEPS
      pw_preprocessor
      pw_sync.binary_semaphore
    GROUPS
      modules
      pw_sync
  )
endif()

if(NOT "${pw_sync.counting_semaphore_BACKEND}" STREQUAL
   "pw_sync.counting_semaphore.NO_BACKEND_SET")
  pw_add_test(pw_sync.counting_semaphore_facade_test
    SOURCES
      counting_semaphore_facade_test.cc
      counting_semaphore_facade_test_c.c
    DEPS
      pw_preprocessor
      pw_sync.counting_semaphore
    GROUPS
      modules
      pw_sync
  )
endif()

if(NOT "${pw_sync.mutex_BACKEND}" STREQUAL "pw_sync.mutex.NO_BACKEND_SET")
  pw_add_test(pw_sync.mutex_facade_test
    SOURCES
      mutex_facade_test.cc
      mutex_facade_test_c.c
    DEPS
      pw_preprocessor
      pw_sync.mutex
    GROUPS
      modules
      pw_sync
  )
endif()

if(NOT "${pw_sync.timed_mutex_BACKEND}" STREQUAL
   "pw_sync.timed_mutex.NO_BACKEND_SET")
  pw_add_test(pw_sync.timed_mutex_facade_test
    SOURCES
      timed_mutex_facade_test.cc
      timed_mutex_facade_test_c.c
    DEPS
      pw_preprocessor
      pw_sync.timed_mutex
    GROUPS
      modules
      pw_sync
  )
endif()

if(NOT "${pw_sync.interrupt_spin_lock_BACKEND}" STREQUAL
   "pw_sync.interrupt_spin_lock.NO_BACKEND_SET")
  pw_add_test(pw_sync.interrupt_spin_lock_facade_test
    SOURCES
      interrupt_spin_lock_facade_test.cc
      interrupt_spin_lock_facade_test_c.c
    DEPS
      pw_preprocessor
      pw_sync.interrupt_spin_lock
    GROUPS
      modules
      pw_sync
  )
endif()

if(NOT "${pw_sync.thread_notification_BACKEND}" STREQUAL
   "pw_sync.thread_notification.NO_BACKEND_SET")
  pw_add_test(pw_sync.thread_notification_facade_test
    SOURCES
      thread_notification_facade_test.cc
    DEPS
      pw_sync.thread_notification
    GROUPS
      modules
      pw_sync
  )
endif()

if(NOT "${pw_sync.timed_thread_notification_BACKEND}" STREQUAL
   "pw_sync.timed_thread_notification.NO_BACKEND_SET")
  pw_add_test(pw_sync.timed_thread_notification_facade_test
    SOURCES
      timed_thread_notification_facade_test.cc
    DEPS
      pw_sync.timed_thread_notification
    GROUPS
      modules
      pw_sync
  )
endif()
