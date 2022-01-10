Example bundle used to test ecbundle
It contains some dummy projects


Development of test-drivers should :

    # 1. Create new bundle and download if required

    ecbundle create --no-color


    # 2. Update created bundle, e.g. when modifying bundle.yml

    ecbundle create --update


    # 3. Build the bundle

    ecbundle build


    # 4. Replace download with existing repository using TEST_BUNDLE_TEST_PROJECT_1_DIR

    rm -rf source build      # cleanup
    git clone https://git.ecmwf.int/scm/ecsdk/test_project_1 existing_test_project_1
    export TEST_BUNDLE_TEST_PROJECT_1_DIR=$(pwd)/existing_test_project_1
    ecbundle create


    # cleanup
    rm -rf source build existing_test_project_1

