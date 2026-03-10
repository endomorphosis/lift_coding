import React from 'react';

const mockAlertSpy = jest.fn();
const mockCanOpenURLSpy = jest.fn();
const mockOpenURLSpy = jest.fn();

jest.mock('react-native', () => {
  const ReactNativeReact = require('react');

  const makeComponent = (name) => {
    const Component = ({ children, ...props }) =>
      ReactNativeReact.createElement(name, props, children);
    Component.displayName = name;
    return Component;
  };

  return {
    Alert: { alert: (...args) => mockAlertSpy(...args) },
    Linking: {
      canOpenURL: (...args) => mockCanOpenURLSpy(...args),
      openURL: (...args) => mockOpenURLSpy(...args),
    },
    StyleSheet: { create: (styles) => styles },
    Button: makeComponent('Button'),
    Modal: makeComponent('Modal'),
    Text: makeComponent('Text'),
    TextInput: makeComponent('TextInput'),
    TouchableOpacity: makeComponent('TouchableOpacity'),
    View: makeComponent('View'),
  };
});

import ActionPromptModal from '../ActionPromptModal';
import EmptyStateCard from '../EmptyStateCard';
import FollowOnTaskCard from '../FollowOnTaskCard';
import InfoCard from '../InfoCard';
import RefreshStatusCard from '../RefreshStatusCard';
import ScreenHeader from '../ScreenHeader';
import SegmentedControl from '../SegmentedControl';
import UICardList from '../UICardList';

function expandTree(node) {
  if (node == null || typeof node === 'boolean') {
    return [];
  }
  if (Array.isArray(node)) {
    return node.flatMap(expandTree);
  }
  if (!React.isValidElement(node)) {
    return [node];
  }
  if (typeof node.type === 'function') {
    return expandTree(node.type(node.props));
  }
  return [node, ...expandTree(node.props?.children)];
}

function collectText(node) {
  return expandTree(node)
    .filter((entry) => typeof entry === 'string' || typeof entry === 'number')
    .map(String)
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function findElement(node, predicate) {
  return expandTree(node).find(
    (entry) => React.isValidElement(entry) && predicate(entry)
  );
}

describe('ActionPromptModal', () => {
  beforeEach(() => {
    mockAlertSpy.mockReset();
  });

  it('renders prompt text and validates empty input before running', () => {
    const onCancel = jest.fn();
    const onRun = jest.fn();
    const onChangeValue = jest.fn();

    const tree = ActionPromptModal({
      visible: true,
      title: 'Rerun URL',
      promptLabel: 'New seed URL',
      value: '',
      onChangeValue,
      onCancel,
      onRun,
    });

    expect(collectText(tree)).toContain('Rerun URL');
    expect(collectText(tree)).toContain('New seed URL');

    const runButton = findElement(tree, (entry) => entry.type === 'Button' && entry.props.title === 'Run');
    runButton.props.onPress();

    expect(mockAlertSpy).toHaveBeenCalledWith(
      'Missing Value',
      'Enter a value before running this action.'
    );
    expect(onRun).not.toHaveBeenCalled();

    const cancelButton = findElement(tree, (entry) => entry.type === 'Button' && entry.props.title === 'Cancel');
    cancelButton.props.onPress();
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('runs when a non-empty value is present', () => {
    const onRun = jest.fn();

    const tree = ActionPromptModal({
      visible: true,
      title: 'Rerun Search',
      promptLabel: 'New dataset query',
      value: 'labor datasets',
      onChangeValue: jest.fn(),
      onCancel: jest.fn(),
      onRun,
    });

    const runButton = findElement(tree, (entry) => entry.type === 'Button' && entry.props.title === 'Run');
    runButton.props.onPress();

    expect(onRun).toHaveBeenCalledTimes(1);
    expect(mockAlertSpy).not.toHaveBeenCalled();
  });
});

describe('RefreshStatusCard', () => {
  it('renders interval, background refresh, and last refreshed text', () => {
    const tree = RefreshStatusCard({
      intervalSeconds: 5,
      backgroundRefreshing: true,
      lastRefreshedAt: '2026-03-08T10:00:00.000Z',
    });

    const text = collectText(tree);
    expect(text).toContain('Auto-refreshing every 5');
    expect(text).toContain('Refreshing in background...');
    expect(text).toContain('Last refreshed:');
  });

  it('renders nothing when no refresh state is present', () => {
    expect(
      RefreshStatusCard({
        intervalSeconds: null,
        backgroundRefreshing: false,
        lastRefreshedAt: null,
        idleLabel: null,
      })
    ).toBeNull();
  });
});

describe('InfoCard', () => {
  it('renders an optional action button and fires it', () => {
    const onActionPress = jest.fn();
    const tree = InfoCard({
      title: 'Last Action',
      lines: ['Task task-123 is ready to track.'],
      actionLabel: 'Open Task Detail',
      onActionPress,
    });

    expect(collectText(tree)).toContain('Last Action');
    expect(collectText(tree)).toContain('Open Task Detail');

    const actionButton = findElement(
      tree,
      (entry) => entry.type === 'TouchableOpacity' && collectText(entry).includes('Open Task Detail')
    );
    actionButton.props.onPress();
    expect(onActionPress).toHaveBeenCalledTimes(1);
  });
});

describe('FollowOnTaskCard', () => {
  it('renders follow-on task metadata and opens task detail', () => {
    const onOpenTask = jest.fn();
    const tree = FollowOnTaskCard({
      followOnTask: {
        task_id: 'task-456',
        state: 'running',
        provider: 'ipfs_accelerate_mcp',
        provider_label: 'IPFS Accelerate',
        capability: 'workflow',
        summary: 'IPFS Accelerate workflow running.',
        result_preview: 'Pinned bafy123.',
        mcp_preferred_execution_mode: 'direct_import',
        mcp_execution_mode: 'mcp_remote',
      },
      onOpenTask,
    });

    expect(collectText(tree)).toContain('Follow-on Task');
    expect(collectText(tree)).toContain('IPFS Accelerate workflow running.');
    expect(collectText(tree)).toContain('Task ID: task-456');
    expect(collectText(tree)).toContain('State: running');
    expect(collectText(tree)).toContain('Provider: IPFS Accelerate');
    expect(collectText(tree)).toContain('Capability: workflow');
    expect(collectText(tree)).toContain('Result: Pinned bafy123.');
    expect(collectText(tree)).toContain('Execution: Remote (local unavailable)');
    expect(collectText(tree)).toContain('Provider ID: ipfs_accelerate_mcp');
    expect(collectText(tree)).toContain('Open Task Detail');

    const openButton = findElement(
      tree,
      (entry) => entry.type === 'TouchableOpacity' && collectText(entry).includes('Open Task Detail')
    );
    openButton.props.onPress();

    expect(onOpenTask).toHaveBeenCalledWith('task-456');
  });
});

describe('UICardList', () => {
  beforeEach(() => {
    mockAlertSpy.mockReset();
    mockCanOpenURLSpy.mockReset();
    mockOpenURLSpy.mockReset();
  });

  it('renders cards, fires action callbacks, opens links, and supports card press', async () => {
    mockCanOpenURLSpy.mockResolvedValue(true);
    mockOpenURLSpy.mockResolvedValue(undefined);
    jest.spyOn(Date, 'now').mockReturnValue(new Date('2026-03-08T10:05:00.000Z').getTime());

    const onActionPress = jest.fn();
    const onCardPress = jest.fn();
    const card = {
      title: 'Dataset Result',
      subtitle: 'dataset_discovery',
      status_badge: 'Running',
      status_tone: 'active',
      is_live: true,
      live_label: 'Live',
      timestamp_label: 'Updated 5m ago',
      sync_hint: 'Syncing task detail...',
      is_syncing: true,
      lines: ['Expanded legal query'],
      deep_link: 'https://example.com/result',
      action_items: [
        {
          id: 'show_result_details',
          label: 'Details',
          phrase: 'show task details',
          execution_mode: 'mcp_remote',
          execution_mode_label: 'Remote',
        },
      ],
      task_id: 'task-123',
    };

    const tree = UICardList({
      cards: [card],
      title: 'Recent Results',
      onActionPress,
      onCardPress,
      cardPressLabel: 'Open Task Detail',
    });

    const text = collectText(tree);
    expect(text).toContain('Recent Results');
    expect(text).toContain('Dataset Result');
    expect(text).toContain('Running');
    expect(text).toContain('Live');
    expect(text).toContain('Updated 5m ago');
    expect(text).toContain('Syncing task detail...');
    expect(text).toContain('Expanded legal query');
    expect(text).toContain('Open Link');
    expect(text).toContain('Open Task Detail');
    expect(text).toContain('Remote');

    const actionButton = findElement(
      tree,
      (entry) => entry.type === 'TouchableOpacity' && collectText(entry).includes('Details')
    );
    actionButton.props.onPress();
    expect(onActionPress).toHaveBeenCalledWith(card.action_items[0], card);

    const detailButton = findElement(
      tree,
      (entry) => entry.type === 'TouchableOpacity' && collectText(entry).includes('Open Task Detail')
    );
    detailButton.props.onPress();
    expect(onCardPress).toHaveBeenCalledWith(card);

    const openLinkButton = findElement(
      tree,
      (entry) => entry.type === 'TouchableOpacity' && collectText(entry).includes('Open Link')
    );
    await openLinkButton.props.onPress();

    expect(mockCanOpenURLSpy).toHaveBeenCalledWith('https://example.com/result');
    expect(mockOpenURLSpy).toHaveBeenCalledWith('https://example.com/result');
    Date.now.mockRestore();
  });

  it('alerts when a deep link is unsupported', async () => {
    mockCanOpenURLSpy.mockResolvedValue(false);

    const tree = UICardList({
      cards: [
        {
          title: 'CID Result',
          deep_link: 'ipfs://bafytest',
          lines: [],
          action_items: [],
        },
      ],
    });

    const openLinkButton = findElement(
      tree,
      (entry) => entry.type === 'TouchableOpacity' && collectText(entry).includes('Open Link')
    );
    await openLinkButton.props.onPress();

    expect(mockAlertSpy).toHaveBeenCalledWith('Unsupported Link', 'ipfs://bafytest');
    expect(mockOpenURLSpy).not.toHaveBeenCalled();
  });
});

describe('SegmentedControl', () => {
  it('renders options and calls onChange with the selected value', () => {
    const onChange = jest.fn();
    const tree = SegmentedControl({
      options: [
        { value: 'all', label: 'All' },
        { value: 'active', label: 'Active' },
      ],
      selectedValue: 'all',
      onChange,
      disabled: false,
    });

    expect(collectText(tree)).toContain('All');
    expect(collectText(tree)).toContain('Active');

    const activeButton = findElement(
      tree,
      (entry) => entry.type === 'TouchableOpacity' && collectText(entry).includes('Active')
    );
    activeButton.props.onPress();

    expect(onChange).toHaveBeenCalledWith('active');
  });
});

describe('ScreenHeader', () => {
  it('renders title, subtitle, and refresh action', () => {
    const onActionPress = jest.fn();
    const tree = ScreenHeader({
      title: 'Notifications',
      subtitle: 'Browse recent notifications.',
      actionLabel: 'Refresh',
      onActionPress,
      actionDisabled: false,
    });

    expect(collectText(tree)).toContain('Notifications');
    expect(collectText(tree)).toContain('Browse recent notifications.');
    expect(collectText(tree)).toContain('Refresh');

    const refreshButton = findElement(
      tree,
      (entry) => entry.type === 'TouchableOpacity' && collectText(entry).includes('Refresh')
    );
    refreshButton.props.onPress();

    expect(onActionPress).toHaveBeenCalledTimes(1);
  });
});

describe('InfoCard', () => {
  it('renders title, accent, and lines', () => {
    const tree = InfoCard({
      title: 'Last Action',
      accent: 'completed',
      lines: ['Pinned bafy123'],
      tone: 'warning',
    });

    expect(collectText(tree)).toContain('Last Action');
    expect(collectText(tree)).toContain('completed');
    expect(collectText(tree)).toContain('Pinned bafy123');
  });
});

describe('EmptyStateCard', () => {
  it('renders a title and message', () => {
    const tree = EmptyStateCard({
      title: 'No results yet',
      message: 'Try another saved view.',
    });

    expect(collectText(tree)).toContain('No results yet');
    expect(collectText(tree)).toContain('Try another saved view.');
  });
});
