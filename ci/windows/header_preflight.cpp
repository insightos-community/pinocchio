// Check the deprecated EigenPy header/macros before the expensive Pinocchio build.
// MSVC defines _WIN32, but does not predefine the legacy WIN32 spelling.
#include <eigenpy/memory.hpp>
EIGENPY_DEFINE_STRUCT_ALLOCATOR_SPECIALIZATION(int)
int main() { return 0; }
