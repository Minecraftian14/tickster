import { useEffect, useState } from 'react';
import {
  Button,
  Container,
  Group,
  Paper,
  Stack,
  Text,
  Title,
  Transition,
} from '@mantine/core';

function App() {
  const [count, setCount] = useState(0);
  const [mounted, setMounted] = useState(true);

  useEffect(() => {
    document.title = `Count: ${count}`;
  }, [count]);

  const increment = () => {
    setCount((current) => current + 1);
    setMounted(false);

    setTimeout(() => {
      setMounted(true);
    }, 50);
  };

  const decrement = () => {
    setCount((current) => current - 1);
  };

  const reset = () => {
    setCount(0);
  };

  return (
    <Container size="xs" py="xl">
      <Paper withBorder shadow="sm" radius="lg" p="xl">
        <Stack align="center">
          <Title order={2}>Animated Counter</Title>

          <Text c="dimmed" ta="center">
            A simple example using React hooks and Mantine.
          </Text>

          <Transition
            mounted={mounted}
            transition="pop"
            duration={300}
            timingFunction="ease"
          >
            {(styles) => (
              <Text
                style={styles}
                fw={700}
                fz={64}
                lh={1}
              >
                {count}
              </Text>
            )}
          </Transition>

          <Group>
            <Button
              variant="light"
              onClick={decrement}
            >
              -
            </Button>

            <Button onClick={increment}>
              +1
            </Button>

            <Button
              variant="subtle"
              color="gray"
              onClick={reset}
            >
              Reset
            </Button>
          </Group>
        </Stack>
      </Paper>
    </Container>
  );
}

export default App;