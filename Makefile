# Include symbols used by test engine manually.
imgui_ldr:
	./gl3w_gen.py --output ../imgui/backends/imgui_impl_opengl3_loader.h --include ../imgui/ --include-symbols glReadPixels GL_PACK_ALIGNMENT GL_FRAMEBUFFER_SRGB --ignore ../imgui/examples/misc ../imgui/backends/imgui_impl_opengl2. ../imgui/imstb

# Include test engine (not public yet) in generation process.
_imgui_ldr:
	./gl3w_gen.py --output ../imgui/backends/imgui_impl_opengl3_loader.h --include ../imgui/ ../imgui_dev/shared/ ../imgui_dev/test_app/ --ignore ../imgui/examples/misc ../imgui/backends/imgui_impl_opengl2. ../imgui/imstb
