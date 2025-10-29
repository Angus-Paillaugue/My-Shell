import 'package:flutter/material.dart';
import 'dart:async';
import 'package:vellum_shell_sync/components/manage_modules_dialog.dart';
import 'package:vellum_shell_sync/modules/module_manager.dart';
import 'pairing_page.dart';
import 'server/socket_manager.dart';
import 'server/database_provider.dart';
import 'modules/module_interface.dart';
import 'dart:math' as math;

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> with TickerProviderStateMixin {

  String? deviceName;
  String? deviceId;
  String? deviceIp;
  String? apiToken;
  bool _online = false;
  final SocketManager _socket = SocketManager();
  final ModuleManager _moduleManager = ModuleManager();
  late VoidCallback _connListener;

  TabController? _tabController;

  @override
  void initState() {
    super.initState();

    _connListener = () {
      debugPrint("Connection status changed: $_online");
      debugPrint("SocketManager isConnected: ${_socket.isConnected.value}");
      if (!mounted) return;
      setState(() {
        _online = _socket.isConnected.value;
        if (_online) {
          // When connected, initialize modules
          _moduleManager.init();
        }
      });
    };
    _socket.isConnected.addListener(_connListener);
    _initialize();

    // Initialize TabController based on the initial active modules
    _updateTabController();
    _moduleManager.activeModules.addListener(_updateTabController);
  }

  Future<void> _initialize() async {
    await _loadDevice(); // Load the device information
    if (deviceId == null) {
      // Handle the case where no device is paired
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const PairingPage()),
      );
    } else {
      await _socket.connect(deviceIp!, token: apiToken);
    }
  }

  Future<void> _loadDevice() async {
    final row = await DatabaseProvider.getFirstPairedDevice();
    if (row != null) {
      final id = row['device_id'] as String;
      final name = (row['name'] as String?) ?? id;
      final ip = row['last_ip'] as String?;
      final token = row['api_token'] as String?;

      setState(() {
        deviceId = id;
        deviceName = name;
        deviceIp = ip;
        apiToken = token;
      });
      debugPrint("Loaded device: $deviceName ($deviceId) at $deviceIp");

      if (deviceIp != null) {
        try {
          await _socket.connect(deviceIp!, token: apiToken);
        } catch (_) {}
      }
    }
  }

  void _updateTabController() {
    final activeModules = _moduleManager.activeModules.value;
    if (_tabController != null) {
      _tabController!.dispose();
    }
    _tabController = TabController(length: activeModules.length, vsync: this);
    setState(() {}); // Trigger a rebuild to use the new TabController
  }

  @override
  void dispose() {
    _socket.isConnected.removeListener(_connListener);
    _moduleManager.activeModules.removeListener(_updateTabController);
    _tabController?.dispose();
    _online = false;
    _socket.disconnect();
    super.dispose();
  }

  Future<void> _disconnect() async {
    if (deviceId != null) {
      await DatabaseProvider.removeLastIp(deviceId!);
    }
    _socket.isConnected.removeListener(_connListener);
    _socket.disconnect();
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (_) => const PairingPage()),
    );
  }

  Future<void> _showManageModulesDialog() async {
    final shouldReload = await showDialog<bool>(
      context: context,
      builder: (context) => const ManageModulesDialog(),
    );

    if (shouldReload == true) {
      // Re-initialize modules
      await _moduleManager.init(); // Ensure modules are reinitialized
    }
  }

  @override
  Widget build(BuildContext context) {
    if (deviceId == null) {
      return const Center(child: CircularProgressIndicator());
    }

    return Scaffold(
      appBar: AppBar(
        title: Text("${_online ? "Connected" : "Connecting"} to $deviceName"),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(kToolbarHeight),
          child: ValueListenableBuilder<List<VellumModule>>(
            valueListenable: _moduleManager.activeModules,
            builder: (context, activeModules, child) {
              if (!_online || activeModules.isEmpty) {
                return const SizedBox.shrink(); // Return an empty widget if no modules are active
              }
              return TabBar(
                controller: _tabController,
                isScrollable: true,
                tabAlignment: TabAlignment.start,
                tabs: activeModules
                    .map(
                      (module) =>
                          Tab(text: module.name, icon: Icon(module.icon)),
                    )
                    .toList(),
              );
            },
          ),
        ),
      ),
      body: ValueListenableBuilder<List<VellumModule>>(
        valueListenable: _moduleManager.activeModules,
        builder: (context, activeModules, child) {
          if (!_online) {
            return const Center(child: CircularProgressIndicator());
          }
          if (activeModules.isEmpty) {
            return const Center(child: Text("No active modules."));
          }
          return TabBarView(
            controller: _tabController,
            // physics: const NeverScrollableScrollPhysics(),
            children: activeModules
                .map((module) => module.buildWidget(context))
                .toList(),
          );
        },
      ),
      floatingActionButton: ExpandableFab(
        distance: 112,
        icon: Icons.settings,
        children: [
          ActionButton(
            onPressed: _showManageModulesDialog,
            icon: const Icon(Icons.extension),
          ),
          ActionButton(
            onPressed: _disconnect,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
    );
  }
}

@immutable
class ExpandableFab extends StatefulWidget {
  const ExpandableFab({
    super.key,
    this.initialOpen,
    this.icon,
    required this.distance,
    required this.children,

  });

  final bool? initialOpen;
  final double distance;
  final IconData? icon;
  final List<Widget> children;

  @override
  State<ExpandableFab> createState() => _ExpandableFabState();
}

class _ExpandableFabState extends State<ExpandableFab>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _expandAnimation;
  bool _open = false;

  @override
  void initState() {
    super.initState();
    _open = widget.initialOpen ?? false;
    _controller = AnimationController(
      value: _open ? 1.0 : 0.0,
      duration: const Duration(milliseconds: 250),
      vsync: this,
    );
    _expandAnimation = CurvedAnimation(
      curve: Curves.fastOutSlowIn,
      reverseCurve: Curves.easeOutQuad,
      parent: _controller,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _toggle() {
    setState(() {
      _open = !_open;
      if (_open) {
        _controller.forward();
      } else {
        _controller.reverse();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox.expand(
      child: Stack(
        alignment: Alignment.bottomRight,
        clipBehavior: Clip.none,
        children: [
          _buildTapToCloseFab(),
          ..._buildExpandingActionButtons(),
          _buildTapToOpenFab(),
        ],
      ),
    );
  }

  Widget _buildTapToCloseFab() {
    return SizedBox(
      width: 56,
      height: 56,
      child: Center(
        child: Material(
          shape: const CircleBorder(),
          clipBehavior: Clip.antiAlias,
          elevation: 4,
          child: InkWell(
            onTap: _toggle,
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Icon(Icons.close, color: Theme.of(context).colorScheme.onSecondary),
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _buildExpandingActionButtons() {
    final children = <Widget>[];
    final count = widget.children.length;
    final step = 90.0 / (count - 1);
    for (
      var i = 0, angleInDegrees = 0.0;
      i < count;
      i++, angleInDegrees += step
    ) {
      children.add(
        _ExpandingActionButton(
          directionInDegrees: angleInDegrees,
          maxDistance: widget.distance,
          progress: _expandAnimation,
          child: widget.children[i],
        ),
      );
    }
    return children;
  }

  Widget _buildTapToOpenFab() {
    return IgnorePointer(
      ignoring: _open,
      child: AnimatedContainer(
        transformAlignment: Alignment.center,
        transform: Matrix4.diagonal3Values(
          _open ? 0.7 : 1.0,
          _open ? 0.7 : 1.0,
          1.0,
        ),
        duration: const Duration(milliseconds: 250),
        curve: const Interval(0.0, 0.5, curve: Curves.easeOut),
        child: AnimatedOpacity(
          opacity: _open ? 0.0 : 1.0,
          curve: const Interval(0.25, 1.0, curve: Curves.easeInOut),
          duration: const Duration(milliseconds: 250),
          child: FloatingActionButton(
            onPressed: _toggle,
            child: Icon(widget.icon ?? Icons.create),
          ),
        ),
      ),
    );
  }
}

@immutable
class _ExpandingActionButton extends StatelessWidget {
  const _ExpandingActionButton({
    required this.directionInDegrees,
    required this.maxDistance,
    required this.progress,
    required this.child,
  });

  final double directionInDegrees;
  final double maxDistance;
  final Animation<double> progress;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: progress,
      builder: (context, child) {
        final offset = Offset.fromDirection(
          directionInDegrees * (math.pi / 180.0),
          progress.value * maxDistance,
        );
        return Positioned(
          right: 4.0 + offset.dx,
          bottom: 4.0 + offset.dy,
          child: Transform.rotate(
            angle: (1.0 - progress.value) * math.pi / 2,
            child: child!,
          ),
        );
      },
      child: FadeTransition(opacity: progress, child: child),
    );
  }
}

@immutable
class ActionButton extends StatelessWidget {
  const ActionButton({super.key, this.onPressed, required this.icon});

  final VoidCallback? onPressed;
  final Widget icon;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Material(
      shape: const CircleBorder(),
      clipBehavior: Clip.antiAlias,
      color: theme.colorScheme.secondary,
      elevation: 4,
      child: IconButton(
        onPressed: onPressed,
        icon: icon,
        color: theme.colorScheme.onSecondary,
      ),
    );
  }
}
